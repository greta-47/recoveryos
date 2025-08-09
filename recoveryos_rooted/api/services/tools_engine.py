def suggest_tool(mood:int, urge:int, sleep_hours:float, isolation:int):
    if urge >= 4:
        return "Urge Surfing — 5-minute guided wave visualization"
    if mood <= 2:
        return "Grounding — 5-4-3-2-1 sensory reset"
    if sleep_hours < 6:
        return "Sleep Hygiene — 10-minute wind-down routine"
    if isolation >= 4:
        return "Connection — Text a supporter or join a 5-min check-in group"
    return "Breathing — Box breathing 4x4"
