"""
All services related to treating and validating image upload (Event Banners) in TicketPlus.
"""

import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

UPLOAD_DIR = Path("app/static/images/events")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


async def upload_banner_image(file: UploadFile) -> str:
    """
    Validates the extension and size of an uploaded image, saves the file
    on the server with a unique name, and returns its relative path.

    Args:
        file (UploadFile): The image file uploaded in the FastAPI request.

    Returns:
        str: The relative path of the saved file (e.g., '/static/images/events/uuid.jpg').

    Raises:
        ValueError: If the file extension is not allowed (.jpg, .jpeg, .png, .webp).
        ValueError: If the file size is greater than 5MB.
    """
    # Extension validation
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Formato de arquivo inválido. Formatos permitidos: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Size validation
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise ValueError("O tamanho do arquivo excede o limite máximo de 5 MB.")

    # Reset the file point
    await file.seek(0)

    # Make sure the final directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Unique filename generation for each image
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = UPLOAD_DIR / unique_filename

    # Use async file write with aiofiles
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(contents)

    # Return path
    return f"/static/images/events/{unique_filename}"


async def delete_banner_image(file_path: str) -> bool:
    """
    Removes a previously saved image from the file system based on its relative path.

    Args:
        file_path (str): The relative path of the image (e.g., '/static/images/events/uuid.jpg').

    Returns:
        bool: True if the file was successfully removed; False if the path is invalid or the file does not exist on disk.

    Raises:
        ValueError: If a permission or system error occurs while trying to delete the file.
    """
    if not file_path:
        return False

    filename = Path(file_path).name
    full_path = UPLOAD_DIR / filename

    try:
        if full_path.exists() and full_path.is_file():
            full_path.unlink()
            return True
        return False
    except OSError as e:
        raise ValueError(f"Erro ao deletar arquivo: {str(e)}")