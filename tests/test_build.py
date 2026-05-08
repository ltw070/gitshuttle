"""Sprint 6: PyInstaller 빌드 설정 파일 검증 테스트.

실제 빌드 실행은 하지 않는다.
spec 파일과 build.ps1 파일의 내용을 정적으로 검증한다.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def test_spec_file_exists():
    """gitshuttle.spec 파일이 프로젝트 루트에 존재해야 한다."""
    spec_path = PROJECT_ROOT / "gitshuttle.spec"
    assert spec_path.exists(), f"gitshuttle.spec 파일이 없음: {spec_path}"


def test_spec_has_entrypoint():
    """spec 파일에 gitshuttle/__main__.py 엔트리포인트가 포함되어야 한다."""
    spec_path = PROJECT_ROOT / "gitshuttle.spec"
    content = spec_path.read_text(encoding='utf-8')
    assert "gitshuttle/__main__.py" in content, (
        "spec 파일에 엔트리포인트 'gitshuttle/__main__.py'가 없음"
    )


def test_spec_has_pythonutf8():
    """spec 파일에 PYTHONUTF8 환경변수 설정이 포함되어야 한다."""
    spec_path = PROJECT_ROOT / "gitshuttle.spec"
    content = spec_path.read_text(encoding='utf-8')
    assert "PYTHONUTF8" in content, (
        "spec 파일에 'PYTHONUTF8' 환경변수 설정이 없음"
    )


def test_spec_is_onefile():
    """spec 파일에 단일 exe 빌드 관련 EXE 설정이 포함되어야 한다."""
    spec_path = PROJECT_ROOT / "gitshuttle.spec"
    content = spec_path.read_text(encoding='utf-8')
    # EXE 생성 시 a.binaries, a.zipfiles, a.datas 가 포함되면 onefile 빌드
    assert "EXE(" in content, "spec 파일에 EXE( 선언이 없음"
    assert "a.binaries" in content, "spec 파일에 a.binaries가 없음 (onefile 빌드 아님)"
    assert "a.zipfiles" in content, "spec 파일에 a.zipfiles가 없음 (onefile 빌드 아님)"


def test_build_script_exists():
    """build.ps1 파일이 프로젝트 루트에 존재해야 한다."""
    build_script = PROJECT_ROOT / "build.ps1"
    assert build_script.exists(), f"build.ps1 파일이 없음: {build_script}"


def test_build_script_has_pyinstaller():
    """build.ps1에 pyinstaller 실행 명령이 포함되어야 한다."""
    build_script = PROJECT_ROOT / "build.ps1"
    content = build_script.read_text(encoding='utf-8')
    assert "pyinstaller" in content.lower(), (
        "build.ps1에 pyinstaller 명령이 없음"
    )
