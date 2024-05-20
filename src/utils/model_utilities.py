"""Module provides utilitary function for model operations"""
import logging
from typing import List

from pydantic import BaseModel
from userprofile.model import UserEditableProfileModel

logger = logging.getLogger(__name__)


def get_model_fields(
        model: BaseModel
) -> List[str]:
    """Extracts list of fields from provided model

    Args:
        model (BaseMode): pydantic model to extract fields from

    Returns:
        list of field names from model
    """
    return list(
        (*model.model_fields,
         *model.model_computed_fields)
    )


def is_model_empty(
        model: BaseModel
) -> bool:
    """Check whether model got no set fields

    Args:
        model (BaseModel): any pydantic model

    Returns:
        False if any of fields is not None,
        True - otherwise
    """
    try:
        for field in model.model_dump().values():
            if field is not None:
                return False
    except Exception as e:
        logger.info(f"It`s not possible to check field of base class {model}")
    return True

