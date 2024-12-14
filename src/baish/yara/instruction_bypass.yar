rule InstructionBypass: Injection
{
    meta:
        // from https://github.com/deadbits/vigil-llm
        category = "Instruction Bypass"
        description = "Detects phrases used to ignore, disregard, or bypass instructions."
        original_author = "Adam M. Swanda"
        explanation = "This file contains phrases that may be used to perform prompt injection."

    strings:
        $bypass_phrase = /(Ignore|Disregard|Skip|Forget|Neglect|Overlook|Omit|Bypass|Pay no attention to|Do not follow|Do not obey).*?(any|all|prior|previous|preceding|above|foregoing|earlier|initial).*?(content|text|instructions|instruction|directives|directive|commands|command|context|conversation|input|inputs|data|message|messages|communication|response|responses|request|requests)/i
    condition:
        $bypass_phrase
}
