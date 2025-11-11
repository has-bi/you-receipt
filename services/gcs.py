"""Google Cloud Storage integration for image uploads."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from google.api_core import exceptions as gcs_exceptions
from google.cloud import storage
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


class GCSUploader:
    """Upload images to Google Cloud Storage."""

    def __init__(self, bucket_name: str, project_id: str, credentials_path: str):
        self.bucket_name = bucket_name
        self.project_id = project_id

        # Initialize GCS client
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        self.client = storage.Client(project=project_id, credentials=credentials)
        self.bucket = self.client.bucket(bucket_name)
        self._uniform_bucket_level_access = False

        try:
            # Reload bucket metadata once so we know if ACLs are disabled
            self.bucket.reload()
            iam_config = getattr(self.bucket, "iam_configuration", None) or {}
            self._uniform_bucket_level_access = bool(
                getattr(iam_config, "uniform_bucket_level_access_enabled", False)
                if not isinstance(iam_config, dict)
                else iam_config.get("uniformBucketLevelAccess", {})
                .get("enabled", False)
            )
            if self._uniform_bucket_level_access:
                logger.info(
                    "Bucket %s has uniform bucket-level access enabled; skipping per-object ACLs",
                    bucket_name,
                )
        except Exception as exc:  # pragma: no cover - best effort metadata fetch
            logger.warning(
                "Could not determine ACL settings for bucket %s: %s",
                bucket_name,
                exc,
            )

    async def upload_file(
        self, file_path: str, original_filename: str
    ) -> Optional[str]:
        """
        Upload file to GCS and return public URL.

        File naming: {year}/{month}/{uuid}_{original_filename}

        Returns: https://storage.googleapis.com/bucket-name/path/to/file.jpg
        """
        try:
            # Generate destination path with timestamp organization
            now = datetime.now()
            year_month_path = f"{now.year}/{now.month:02d}"
            unique_id = uuid.uuid4().hex[:8]

            # Clean filename (remove special chars)
            clean_filename = "".join(
                c for c in original_filename if c.isalnum() or c in "._- "
            )
            destination_blob_name = f"{year_month_path}/{unique_id}_{clean_filename}"

            # Upload file
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(file_path)

            # Make blob publicly accessible
            await self.make_blob_public(destination_blob_name)

            # Generate public URL
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{destination_blob_name}"

            logger.info(f"Uploaded {original_filename} to {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"Error uploading file to GCS: {e}")
            return None

    async def upload_from_bytes(
        self, file_bytes: bytes, filename: str
    ) -> Optional[str]:
        """
        Upload file from bytes to GCS and return public URL.

        Useful for uploading from memory without saving to disk first.
        """
        try:
            # Generate destination path
            now = datetime.now()
            year_month_path = f"{now.year}/{now.month:02d}"
            unique_id = uuid.uuid4().hex[:8]

            # Clean filename
            clean_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
            destination_blob_name = f"{year_month_path}/{unique_id}_{clean_filename}"

            # Upload bytes
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_string(file_bytes)

            # Make blob publicly accessible
            await self.make_blob_public(destination_blob_name)

            # Generate public URL
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{destination_blob_name}"

            logger.info(f"Uploaded {filename} to {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"Error uploading bytes to GCS: {e}")
            return None

    async def make_blob_public(self, blob_name: str):
        """Make uploaded blob publicly accessible."""
        if self._uniform_bucket_level_access:
            logger.debug(
                "Bucket has uniform bucket-level access; skipping make_public for %s",
                blob_name,
            )
            return

        try:
            blob = self.bucket.blob(blob_name)
            blob.make_public()
            logger.debug(f"Made blob {blob_name} public")
        except gcs_exceptions.BadRequest as exc:
            message = str(exc)
            if "uniform bucket-level access" in message:
                self._uniform_bucket_level_access = True
                logger.warning(
                    "Uniform bucket-level access detected for bucket %s; "
                    "skipping make_public from now on",
                    self.bucket_name,
                )
                return
            logger.error(f"Error making blob public: {exc}")
            raise
        except Exception as e:  # pragma: no cover - defensive logging
            logger.error(f"Unexpected error making blob public: {e}")
            raise

    def delete_file(self, blob_name: str) -> bool:
        """Delete a file from GCS bucket."""
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            logger.info(f"Deleted {blob_name} from GCS")
            return True
        except Exception as e:
            logger.error(f"Error deleting file from GCS: {e}")
            return False

    def get_signed_url(
        self, blob_name: str, expiration_minutes: int = 60
    ) -> Optional[str]:
        """
        Generate a signed URL for private access (alternative to public URLs).

        Args:
            blob_name: Path to blob in bucket
            expiration_minutes: URL validity duration

        Returns: Signed URL string
        """
        try:
            blob = self.bucket.blob(blob_name)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET",
            )
            return url
        except Exception as e:
            logger.error(f"Error generating signed URL: {e}")
            return None
