
@echo off
cd /d D:\EnviroTrack

if not exist logs mkdir logs

echo. >> logs\scheduled_pipeline.log
echo ======================================== >> logs\scheduled_pipeline.log
echo Pipeline started: %DATE% %TIME% >> logs\scheduled_pipeline.log
echo ======================================== >> logs\scheduled_pipeline.log

uv run python -m envirotrack.pipeline >> logs\scheduled_pipeline.log 2>&1

echo Pipeline exit code: %ERRORLEVEL% >> logs\scheduled_pipeline.log
