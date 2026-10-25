"""
Emailing services background loop.

This module provides an async loop that will periodically run the emailing
service work. The actual emailing algorithm will be implemented later; for
now this loop provides a stable, configurable runner that can be started as
an asyncio background task from `process_switch`.

Configuration (environment variables):
  - EMAILING_SERVICES_INTERVAL_SECONDS: polling interval in seconds.
	If not set, the loop will default to 300 seconds (5 minutes).
  - EMAILING_SERVICES_INTERVAL_MINUTES: alternative to provide minutes.
	If both are set, seconds takes precedence.

The loop handles cancellation cleanly and logs startup/shutdown events.
"""

import os
import asyncio
from typing import Optional
from utils.async_log import get_logger
import json
from sqlalchemy import text
from database import async_session_factory
from pathlib import Path
import urllib.request
import urllib.error
import ssl

logger = get_logger("emailing_services")


# Global cached Brevo API key (loaded once at startup)
BREVO_API_KEY: Optional[str] = None


def _get_interval_seconds() -> int:
	"""Return the emailing loop interval in seconds.

	Priority:
	  1. EMAILING_SERVICES_INTERVAL_SECONDS
	  2. EMAILING_SERVICES_INTERVAL_MINUTES (converted to seconds)
	  3. default 300 (5 minutes)
	"""
	seconds = os.getenv("EMAILING_SERVICES_INTERVAL_SECONDS")
	minutes = os.getenv("EMAILING_SERVICES_INTERVAL_MINUTES")
	if seconds:
		try:
			return int(seconds)
		except ValueError:
			logger.warning("Invalid EMAILING_SERVICES_INTERVAL_SECONDS, falling back")
	if minutes:
		try:
			return int(minutes) * 60
		except ValueError:
			logger.warning("Invalid EMAILING_SERVICES_INTERVAL_MINUTES, falling back")
	return 300  # default 5 minutes


def _get_concurrency() -> int:
	"""Return max concurrency for sending emails."""
	try:
		return int(os.getenv('EMAILING_SERVICES_CONCURRENCY', '5'))
	except Exception:
		return 5


async def emailing_services_loop() -> None:
	"""Main async loop for emailing services.

	This function runs forever until cancelled. It performs whatever work is
	required by the emailing service (placeholder for now) and then sleeps for
	the configured interval. The actual emailing algorithm will be added later
	in this module or by calling into helper functions.
	"""
	interval = _get_interval_seconds()

	# Load BREVO API key once at startup
	# Local: use `utils.local_credentials` (no fallback)
	# Production: fetch from Azure Key Vault via `credential_manager.get_brevo_api_key()`
	global BREVO_API_KEY
	try:
		if os.getenv('AT_LOCAL_MACHINE', 'False').lower() in ('true', '1', 'yes'):
			from utils.local_credentials import get_local_brevo_api_key, log_local_usage

			BREVO_API_KEY = get_local_brevo_api_key() or os.getenv('BREVO_API', '')
			log_local_usage('brevo_api')
			if BREVO_API_KEY:
				logger.info("🔑 BREVO API key loaded from local credentials")
			else:
				logger.warning("⚠️ BREVO API key not set in local credentials; set `brevo_api` in utils/local_credentials.py or export BREVO_API")
		else:
			# Production: try Azure Key Vault via credential_manager, with environment fallback
			from utils.credential_manager import credential_manager

			try:
				brevo_info = await credential_manager.get_brevo_api_key()
				if isinstance(brevo_info, dict):
					BREVO_API_KEY = brevo_info.get('brevo_api') or os.getenv('BREVO_API', '')
				else:
					BREVO_API_KEY = brevo_info or os.getenv('BREVO_API', '')

				if BREVO_API_KEY:
					logger.info("🔑 BREVO API key loaded from Azure Key Vault or environment")
				else:
					logger.warning("⚠️ BREVO API key not found in vault or environment; emailing may fail until provided")
			except Exception as e:
				logger.error(f"❌ Failed to get Brevo API key from credential_manager: {e}")
				BREVO_API_KEY = os.getenv('BREVO_API', '')

	except Exception as e:
		logger.error(f"❌ Failed to load BREVO API key at startup: {e}")
		BREVO_API_KEY = os.getenv('BREVO_API', '')

	logger.info(f"🚀 Emailing services loop starting (interval={interval}s)")

	try:
		while True:
			try:
				processed = await process_pending_emails()
				logger.info(f"emailing_services: processed {processed} emails this tick")
			except Exception as e:
				logger.error(f"Error while running emailing_services iteration: {e}")

			# Sleep for configured interval (re-read env on each loop could be added later)
			await asyncio.sleep(interval)

	except asyncio.CancelledError:
		# Clean shutdown path when task.cancel() is called
		logger.info("🛑 Emailing services loop cancelled, performing cleanup")
		# Place any cleanup logic here (flush queues, close connections)
		raise
	except Exception as e:
		logger.error(f"Unexpected fatal error in emailing_services_loop: {e}")
		raise


__all__ = ["emailing_services_loop"]


# Template cache
_USER_DIG_TEMPLATE: Optional[dict] = None


def _load_user_dig_template() -> dict:
	"""Load and cache the user_dig_request template JSON from tasks directory."""
	global _USER_DIG_TEMPLATE
	if _USER_DIG_TEMPLATE is not None:
		return _USER_DIG_TEMPLATE

	tpl_path = Path(__file__).resolve().parents[0] / "tasks" / "use_dig_request.json"
	try:
		with open(tpl_path, "r", encoding="utf-8") as fh:
			_USER_DIG_TEMPLATE = json.load(fh)
			return _USER_DIG_TEMPLATE
	except Exception as e:
		logger.error(f"❌ Failed to load user_dig_request template: {e}")
		_USER_DIG_TEMPLATE = {}
		return _USER_DIG_TEMPLATE


async def send_via_brevo(payload: dict) -> bool:
	"""Send payload to Brevo SMTP API using built-in urllib (no extra deps).

	Returns True on success (messageId returned), False otherwise.
	"""
	global BREVO_API_KEY

	if not BREVO_API_KEY:
		logger.error("❌ BREVO API key is not configured; cannot send email")
		return False

	url = "https://api.brevo.com/v3/smtp/email"
	body = json.dumps(payload).encode("utf-8")
	headers = {
		"accept": "application/json",
		"api-key": BREVO_API_KEY,
		"content-type": "application/json",
	}

	def _sync_post():
		ctx = ssl.create_default_context()
		req = urllib.request.Request(url, data=body, headers=headers, method="POST")
		try:
			with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
				resp_data = resp.read().decode("utf-8")
				logger.debug(f"Brevo response raw: {resp_data}")
				try:
					parsed = json.loads(resp_data)
				except Exception:
					parsed = None
				return (True, parsed)
		except urllib.error.HTTPError as he:
			try:
				err_body = he.read().decode("utf-8")
			except Exception:
				err_body = str(he)
			logger.error(f"Brevo HTTP error: {he.code} - {err_body}")
			try:
				return (False, json.loads(err_body))
			except Exception:
				return (False, {"error": err_body})
		except Exception as e:
			logger.error(f"Brevo request failed: {e}")
			return (False, {"error": str(e)})

	loop = asyncio.get_running_loop()
	success, resp = await loop.run_in_executor(None, _sync_post)

	if success and isinstance(resp, dict) and resp.get("messageId"):
		logger.info(f"✅ Email sent via Brevo, messageId={resp.get('messageId')}")
		return True

	logger.error(f"❌ Brevo send failed or returned unexpected response: {resp}")
	return False


async def handle_user_dig_request(session, recipient_email: str, body_data: dict, requested_at) -> bool:
	"""Prepare the template for a user_dig_request and send it.

	Replacements (only the ones you requested):
	  - recipient email in `to[0]['email']`
	  - replace marker `//TASK_ID//` inside `htmlContent` with body_data['task_id']
	"""
	template = _load_user_dig_template()
	if not template:
		logger.error("No user_dig_request template available; skipping email")
		return False

	# Work on a copy to avoid mutating cached template
	tpl = json.loads(json.dumps(template))

	# Change recipient
	try:
		if 'to' in tpl and isinstance(tpl['to'], list) and tpl['to']:
			tpl['to'][0]['email'] = recipient_email
		else:
			tpl['to'] = [{"email": recipient_email, "name": "SentinelFlux Client"}]
	except Exception:
		tpl['to'] = [{"email": recipient_email, "name": "SentinelFlux Client"}]

	# Replace TASK_ID marker in htmlContent
	task_id = ''
	try:
		task_id = body_data.get('task_id', '') if isinstance(body_data, dict) else ''
	except Exception:
		task_id = ''

	if 'htmlContent' in tpl and isinstance(tpl['htmlContent'], str):
		tpl['htmlContent'] = tpl['htmlContent'].replace('//TASK_ID//', task_id)

	# Send via Brevo (placeholder)
	sent = await send_via_brevo(tpl)
	return bool(sent)


async def process_pending_emails(limit: int = 100) -> int:
	"""Fetch pending emailing_data rows and process them.

	Returns the number of processed rows.
	"""
	processed = 0

	try:
		# Select rows and process them inside the same transaction to avoid
		# intermediate status updates. This keeps the selected rows locked
		# until we update their final status (success/error).
		async with async_session_factory() as session:
			async with session.begin():
				select_q = text(
					"SELECT id, email, send_type, is_done, requested_at, body_data "
					"FROM emailing_data "
					"WHERE is_done = false "
					"ORDER BY requested_at ASC "
					"FOR UPDATE SKIP LOCKED LIMIT :limit"
				)
				result = await session.execute(select_q, {"limit": limit})
				rows = result.fetchall()

				if not rows:
					logger.debug("No pending emails found")
					return 0

				# Process each row while locks are held; update final status only
				for row in rows:
					id = row[0]
					email = row[1]
					send_type = row[2]
					requested_at = row[4]
					body_data = row[5]

					success = False
					try:
						if send_type == 'user_dig_request':
							success = await handle_user_dig_request(session, email, body_data, requested_at)
						else:
							logger.debug(f"Skipping unknown send_type: {send_type}")
					except Exception as e:
						logger.error(f"Error processing row id={id}: {e}")

					# Update final status based on result; mark is_done true regardless
					try:
						if success:
							await session.execute(
								text("UPDATE emailing_data SET is_done = true, status = 'success' WHERE id = :id"),
								{"id": id}
							)
							processed += 1
						else:
							await session.execute(
								text("UPDATE emailing_data SET is_done = true, status = 'error' WHERE id = :id"),
								{"id": id}
							)
					except Exception as e:
						logger.error(f"Failed to update status for id={id}: {e}")

				# transaction will commit here

	except Exception as e:
		logger.error(f"❌ Failed to fetch pending emails: {e}")

	return processed


