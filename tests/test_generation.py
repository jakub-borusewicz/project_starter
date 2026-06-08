import pathlib
import copier

from tests.consts import BASE_DIR



class TestProjectGeneration:

    def test_generation_succeed(self, tmp_path: pathlib.Path) -> None:
        # given
        generated_project_dir = tmp_path / "test_project"

        # when
        copier.run_copy(
            src_path=str(BASE_DIR),
            dst_path=generated_project_dir,
            data={
                "project_name": "test_project",
            },
            unsafe=True,
        )

        # then
        assert (tmp_path / "test_project").exists()