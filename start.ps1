#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start the AfwezigheidsAttest application (Frontend + Azure Function)
.DESCRIPTION
    This script starts both the frontend development server and the Azure Function
    in separate terminal windows for easy demo and development.
#>

Write-Host "Starting AfwezigheidsAttest Application..." -ForegroundColor Cyan
Write-Host ""

# Reload PATH to ensure Azure CLI is available
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Get the script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start Azure Function in a new terminal
Write-Host "Starting Azure Function..." -ForegroundColor Yellow
$funcPath = Join-Path $scriptPath "api"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$funcPath'; Write-Host 'Azure Function Starting...' -ForegroundColor Green; func start"

# Wait a moment for the function to initialize
Write-Host "Waiting for Azure Function to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Start Frontend in a new terminal
Write-Host "Starting Frontend..." -ForegroundColor Yellow
$frontendPath = Join-Path $scriptPath "frontend"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; Write-Host 'Frontend Starting...' -ForegroundColor Green; npm run dev"

Write-Host ""
Write-Host "Application is starting!" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend will be available at: http://localhost:5173/" -ForegroundColor Cyan
Write-Host "Azure Function will be available at: http://localhost:7071/api/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Two new terminal windows have been opened." -ForegroundColor White
Write-Host "Close those windows to stop the application." -ForegroundColor White
Write-Host ""
