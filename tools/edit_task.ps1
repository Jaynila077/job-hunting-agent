param(
    [Parameter(Mandatory = $true)]
    [string]$Instruction,

    [ValidateSet("groq", "ollama")]
    [string]$Provider = "groq"
)

# ==========================================
# Configuration
# ==========================================

$ProjectFile = ".ai/PROJECT.md"
$TaskFile = ".ai/TASK.md"
$OutputFile = ".ai/TASK.draft.md"
$EnvFile = ".env"

# ==========================================
# Validate files
# ==========================================

if (-not (Test-Path $TaskFile)) {
    Write-Error "Missing $TaskFile"
    exit 1
}

# ==========================================
# Load .env
# ==========================================

$GroqApiKey = $null

if ($Provider -eq "groq") {

    if (-not (Test-Path $EnvFile)) {
        Write-Error "Missing .env file."
        Write-Host ""
        Write-Host "Create .env in the project root with:"
        Write-Host "GROQ_API_KEY=gsk_your_actual_key_here"
        exit 1
    }

    Get-Content $EnvFile | ForEach-Object {

        $Line = $_.Trim()

        # Ignore empty lines and comments
        if ($Line -and -not $Line.StartsWith("#")) {

            $Parts = $Line -split "=", 2

            if ($Parts.Count -eq 2) {

                $Name = $Parts[0].Trim()
                $Value = $Parts[1].Trim()

                if ($Name -eq "GROQ_API_KEY") {
                    $GroqApiKey = $Value
                }
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($GroqApiKey)) {
        Write-Error "GROQ_API_KEY not found in .env"
        exit 1
    }
}

# ==========================================
# Read project files
# ==========================================

$TaskContent = Get-Content $TaskFile -Raw

$ProjectContent = ""

if (Test-Path $ProjectFile) {
    $ProjectContent = Get-Content $ProjectFile -Raw
}

# ==========================================
# Build prompt
# ==========================================

$Prompt = @"
You are an editor for .ai/TASK.md.

Your job is to modify the EXISTING TASK.md according to the user's instruction.

IMPORTANT RULES:

1. TASK.md is the source of truth for the current task.

2. Preserve the existing structure and formatting.

3. Preserve existing information unless the user's instruction requires changing it.

4. Make only the changes necessary to accurately reflect the user's instruction.

5. Do not invent requirements, decisions, constraints, features, or scope.

6. Do not expand the scope.

7. Do not make architecture decisions.

8. Do not choose technologies or implementation approaches unless they already exist
   in TASK.md or PROJECT.md and the user explicitly asks to preserve them.

9. Do not write code.

10. Do not rewrite unchanged sections unnecessarily.

11. Return the COMPLETE revised TASK.md.

12. Output ONLY the revised TASK.md.

13. Do NOT output reasoning, analysis, explanations, commentary, or introductory text.

14. Do NOT output markdown code fences.

15. When the user's instruction changes the phase, purpose, or status of the task,
    identify existing content that directly contradicts the new instruction and
    update or remove ONLY that contradictory content.

16. Do not replace removed contradictory content with your own interpretation
    of what the new phase should contain.

17. Do not invent new requirements merely because they are commonly associated
    with the new phase.

18. The USER decides WHAT the task is.
    You only maintain TASK.md so that it accurately reflects the user's intent.

19. If the user says that another agent or person will handle the next phase,
    do not define that phase's work yourself.

20. Existing product requirements and decisions should normally be preserved as
    context when moving between phases, unless the user explicitly says they
    are no longer relevant.

21. If a previous phase is complete, update its status appropriately rather than
    pretending its requirements never existed.

22. Resolve contradictions caused directly by the user's instruction, but do not
    make unrelated cleanup changes.

23. If the user's instruction is ambiguous, make the smallest reasonable change
    rather than inventing additional meaning.
23. When moving to a new phase, do not populate the task with the
    typical activities, requirements, deliverables, or technical
    details of that phase.

24. A phase transition should primarily update the task's title,
    type, objective, status, constraints, scope, and other sections
    that are directly affected by the user's instruction.

25. Do not convert a general instruction such as "move to the
    architecture phase" into a detailed architecture specification.
    The purpose of TASK.md is to state what the next phase is,
    not to perform that phase.

26. If the user says "Claude will design the architecture", preserve
    that delegation. Do not perform or predefine Claude's architectural
    work.

27. When the user's instruction moves TASK.md into a new phase,
    update wording that refers to the new phase as something that
    will happen later. Do not leave stale temporal references such
    as "deferred to the architecture phase" when the task is already
    the architecture phase.

28. Do not create contradictions between the task's current phase
    and its constraints, requirements, status, or open questions.

29. Distinguish between describing WHAT the current phase must
    accomplish and actually performing that work. It is acceptable
    to state the deliverable of the current phase, but do not
    perform the deliverable inside TASK.md.

PROJECT CONTEXT:
--- BEGIN PROJECT.md ---
$ProjectContent
--- END PROJECT.md ---

CURRENT TASK.md:
--- BEGIN TASK.md ---
$TaskContent
--- END TASK.md ---

USER INSTRUCTION:
--- BEGIN INSTRUCTION ---
$Instruction
--- END INSTRUCTION ---

Now modify the EXISTING TASK.md according to the user's instruction.

Return ONLY the complete revised TASK.md.
"@

# ==========================================
# Call model
# ==========================================

if ($Provider -eq "ollama") {

    Write-Host "Using local Ollama / Qwen 8B..."

    $Result = ollama run qwen3:8b $Prompt

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Ollama failed."
        exit 1
    }
}

elseif ($Provider -eq "groq") {

    Write-Host "Using Groq / GPT-OSS 20B..."

    $Headers = @{
        "Authorization" = "Bearer $GroqApiKey"
        "Content-Type"  = "application/json"
    }

    $Body = @{
        model = "openai/gpt-oss-20b"

        messages = @(
            @{
                role    = "user"
                content = $Prompt
            }
        )

        reasoning_effort = "low"
        temperature = 0.1
        max_completion_tokens = 12000

    } | ConvertTo-Json -Depth 10

    try {

        $Response = Invoke-RestMethod `
            -Uri "https://api.groq.com/openai/v1/chat/completions" `
            -Method Post `
            -Headers $Headers `
            -Body $Body

        $Result = $Response.choices[0].message.content
    }
    catch {

        Write-Error "Groq API request failed."
        Write-Error $_
        exit 1
    }
}

# ==========================================
# Validate output
# ==========================================

$Result = $Result.Trim()

if ([string]::IsNullOrWhiteSpace($Result)) {
    Write-Error "Model returned an empty result."
    exit 1
}

# Remove accidental markdown fences
$Result = $Result -replace '^```markdown\s*', ''
$Result = $Result -replace '^```\s*', ''
$Result = $Result -replace '\s*```$', ''

$Result = $Result.Trim()

# ==========================================
# Write draft
# ==========================================

$Result | Set-Content $OutputFile -Encoding UTF8

Write-Host ""
Write-Host "Draft created:"
Write-Host $OutputFile
Write-Host ""
Write-Host "Provider: $Provider"
Write-Host ""
Write-Host "Review the draft before replacing TASK.md."