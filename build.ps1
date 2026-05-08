# build.ps1 — GitShuttle Windows 빌드 자동화 스크립트
# 실행: .\build.ps1
# 출력: dist\gitshuttle.exe (단일 실행 파일)

# 한글 출력 인코딩 설정
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== GitShuttle 빌드 시작 ===" -ForegroundColor Cyan

# PyInstaller 설치 확인 및 설치
Write-Host "PyInstaller 설치 확인 중..."
$pyinstallerCheck = python -m pip show pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller가 설치되어 있지 않습니다. 설치를 진행합니다..." -ForegroundColor Yellow
    python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PyInstaller 설치 실패." -ForegroundColor Red
        exit 1
    }
    Write-Host "PyInstaller 설치 완료." -ForegroundColor Green
} else {
    Write-Host "PyInstaller가 이미 설치되어 있습니다." -ForegroundColor Green
}

# 이전 빌드 결과물 정리
if (Test-Path "dist\gitshuttle.exe") {
    Write-Host "이전 빌드 결과물 삭제 중..."
    Remove-Item "dist\gitshuttle.exe" -Force
}

# PyInstaller 빌드 실행
Write-Host "빌드 실행 중: pyinstaller gitshuttle.spec --clean" -ForegroundColor Cyan
python -m PyInstaller gitshuttle.spec --clean

if ($LASTEXITCODE -ne 0) {
    Write-Host "빌드 실패. pyinstaller 종료 코드: $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

# 빌드 성공 여부 확인
if (Test-Path "dist\gitshuttle.exe") {
    $exeSize = (Get-Item "dist\gitshuttle.exe").Length / 1MB
    Write-Host "빌드 성공: dist\gitshuttle.exe (크기: $([math]::Round($exeSize, 1)) MB)" -ForegroundColor Green
    Write-Host "=== 빌드 완료 ===" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "빌드 실패: dist\gitshuttle.exe 파일이 생성되지 않았습니다." -ForegroundColor Red
    exit 1
}
