"""Tiny local Pydantic compatibility layer for offline demo environments.

The public project still documents Pydantic as the intended dependency. This
fallback exists so the demo can run on locked-down servers where packages cannot
be installed.
"""

from copy import deepcopy
from typing import Any, Callable, Dict, get_args, get_origin


class _FieldInfo:
    def __init__(self, default: Any = None, default_factory: Callable[[], Any] = None) -> None:
        """Store default values for the local Field helper."""
        # This mirrors only the tiny subset the demo models need.
        self.default = default
        self.default_factory = default_factory

    def make_default(self) -> Any:
        """Create a fresh default value for one model field."""
        # Mutable defaults are copied so model instances do not share state.
        if self.default_factory is not None:
            return self.default_factory()
        return deepcopy(self.default)


def Field(default: Any = None, default_factory: Callable[[], Any] = None) -> _FieldInfo:
    """Return local field metadata for fallback BaseModel defaults."""
    # The signature matches the project's limited Pydantic usage.
    return _FieldInfo(default=default, default_factory=default_factory)


class BaseModel:
    def __init__(self, **data: Any) -> None:
        """Populate annotated fields from keyword data."""
        # This fallback intentionally implements only simple model behavior.
        annotations = getattr(self.__class__, "__annotations__", {})
        for name, annotation in annotations.items():
            class_value = getattr(self.__class__, name, None)
            if name in data:
                value = data[name]
            elif isinstance(class_value, _FieldInfo):
                value = class_value.make_default()
            elif class_value is not None:
                value = deepcopy(class_value)
            else:
                value = None
            setattr(self, name, self._coerce(annotation, value))
        for name, value in data.items():
            if name not in annotations:
                setattr(self, name, value)

    @classmethod
    def _coerce(cls, annotation: Any, value: Any) -> Any:
        """Coerce nested lists and BaseModel dictionaries when possible."""
        # The real Pydantic dependency handles many more cases.
        origin = get_origin(annotation)
        args = get_args(annotation)
        if origin in (list, tuple) and args:
            return [cls._coerce(args[0], item) for item in (value or [])]
        if origin is dict:
            return value or {}
        if isinstance(value, dict) and isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation(**value)
        return value

    def dict(self) -> Dict[str, Any]:
        """Return a plain dictionary representation."""
        # Nested fallback models are recursively converted.
        return {key: self._to_plain(value) for key, value in self.__dict__.items()}

    def model_dump(self) -> Dict[str, Any]:
        """Expose a Pydantic v2-style dump method."""
        # This keeps code compatible with both real and fallback models.
        return self.dict()

    @classmethod
    def _to_plain(cls, value: Any) -> Any:
        """Convert nested fallback models, lists, and dicts to plain data."""
        # json.dump can only serialize plain Python structures.
        if isinstance(value, BaseModel):
            return value.dict()
        if isinstance(value, list):
            return [cls._to_plain(item) for item in value]
        if isinstance(value, dict):
            return {key: cls._to_plain(item) for key, item in value.items()}
        return value

