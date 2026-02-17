# Create RDS Session
# Creates a new Remote Desktop Session on Windows Server
#
# Parameters:
#   -UserName: Windows user to create the session for
#   -PatientId: Patient UUID for logging/tracking
#
# Returns: RDS Session ID (stdout)

param(
    [Parameter(Mandatory=$true)]
    [string]$UserName,

    [Parameter(Mandatory=$true)]
    [string]$PatientId
)

# Create new RDS session
# In production, this would use:
# - qwinsta to check existing sessions
# - logoff to clean up stale sessions
# - New-RDUserSession or equivalent cmdlet
# - Return the session ID

$SessionId = "RDS-SESSION-" + (Get-Random -Minimum 10000 -Maximum 99999)

Write-Host "Created session $SessionId for user $UserName (patient: $PatientId)"

# Return session ID to stdout
Write-Output $SessionId
