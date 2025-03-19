@echo off
setlocal enabledelayedexpansion

:: ���ô���ҳΪ GBK
chcp 936 >nul
title My Dream Moments ������

cls
echo ====================================
echo        My Dream Moments ������
echo ====================================
echo.
echo �X�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�[
echo �U      My Dream Moments - AI Chat   �U
echo �U      Created with Heart by umaru  �U
echo �^�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�a
echo.

:: ������ʱpython����
set "python_home=%cd%\Python310"
if not exist "!python_home!" (
    rem ��ѹPython�ļ�
    echo ��װpython���������ڵ����Ĵ����е����ʼ
    start /wait Python310.exe
    echo Done
    rem ����PIP
    Python310\python -m ensurepip
    copy Python310\Scripts\pip3.10.exe Python310\Scripts\pip.exe
)
rem ������ʱ��������
set "path=!python_home!;!python_home!\Scripts;!path!"
echo ��ǰPATH: "!path!"
rem �������
python --version
if errorlevel 1 (
    echo Python��ʱ������װ����
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
python oneBotMain.py

:: ��������쳣�˳�����ͣ��ʾ������Ϣ
if errorlevel 1 (
    echo �������г���
    pause
)

:: �˳����⻷��
deactivate