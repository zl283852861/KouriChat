@echo off
setlocal enabledelayedexpansion

:: ���ô���ҳΪ GBK
chcp 936 >nul
title KouriChat ������

cls
echo ====================================
echo        KouriChat ������
echo ====================================
echo.
echo �X�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�[
echo �U      KouriChat - AI Chat   �U
echo �U      Created with Heart by umaru  �U
echo �^�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�a
echo.

:: ��� Python �Ƿ��Ѱ�װ
python --version >nul 2>&1
if errorlevel 1 (
    echo Pythonδ��װ�����Ȱ�װPython
    pause
    exit /b 1
)

:: ��� Python �汾
for /f "tokens=2" %%I in ('python -V 2^>^&1') do set PYTHON_VERSION=%%I
for /f "tokens=2 delims=." %%I in ("!PYTHON_VERSION!") do set MINOR_VERSION=%%I
if !MINOR_VERSION! GEQ 13 (
    echo ��֧�� Python 3.13 �����ϰ汾
    echo ��ǰPython�汾: !PYTHON_VERSION!
    echo ��ʹ�� Python 3.12 ����Ͱ汾
    pause
    exit /b 1
)

:: �������⻷��Ŀ¼
set VENV_DIR=.venv

:: ������⻷���Ƿ����
if not exist %VENV_DIR% (
    echo ���ڴ������⻷��...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo �������⻷��ʧ��
        pause
        exit /b 1
    )
)

:: �������⻷��
call %VENV_DIR%\Scripts\activate.bat

:: ��װ����
if exist requirements.txt (
    echo ���ڰ�װ����...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ��װ����ʧ��
        pause
        exit /b 1
    )
)

:: ���г���
echo ������������...
python run_config_web.py

:: ��������쳣�˳�����ͣ��ʾ������Ϣ
if errorlevel 1 (
    echo �������г���
    pause
)

:: �˳����⻷��
deactivate