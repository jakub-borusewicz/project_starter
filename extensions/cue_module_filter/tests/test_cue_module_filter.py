import pytest
from jinja2 import Environment

from extensions.cue_module_filter.cue_module_filter import CueModuleNameFilterExtension


@pytest.fixture
def env():
    return Environment(extensions=[CueModuleNameFilterExtension])


class TestCueModuleNameFilterExtension:

    def test_filters_cue_name(self, env: Environment) -> None:
        # given
        invalid_cue_name = "project_starter"

        # when
        result = env.from_string("{{project_name|cue_name_chars}}", globals={"project_name": invalid_cue_name})

        # then
        assert result.render() == "projectstarter"
