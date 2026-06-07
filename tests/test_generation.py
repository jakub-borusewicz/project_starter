import pathlib
import copier
from copier import settings

from tests.consts import BASE_DIR



class TestProjectGeneration:

    def test_generation_succeed(self, tmp_path: pathlib.Path) -> None:
        # given

        # when
        copier.run_copy(
            src_path=str(BASE_DIR),
            dst_path=tmp_path,
            data={
                "project_name": "test_project",
            },
            unsafe=True,
            # settings=settings.Settings(
            #     trust=True
            # )
        )

        # then
        assert (tmp_path / "test_project").exists()