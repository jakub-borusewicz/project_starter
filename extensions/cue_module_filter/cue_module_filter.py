from jinja2.ext import Extension
from jinja2 import Environment

def cue_name_chars(value: str) -> str:
    return value.replace("_", "")


class CueModuleNameFilterExtension(Extension):
    """
    https://cuelang.org/docs/reference/modules/#module-path
    """
    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)
        environment.filters["cue_name_chars"] = cue_name_chars