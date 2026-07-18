from dataclasses import dataclass, field


@dataclass(slots=True)
class ConfluenceResult:
    call_score: int = 0
    put_score: int = 0
    reasons_call: list[str] = field(default_factory=list)
    reasons_put: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)


class ConfluenceService:
    def evaluate(self, data: dict, *, stale: bool = False, connection_healthy: bool = True) -> ConfluenceResult:
        r = ConfluenceResult()
        if stale: r.blocks.append("Dados atrasados")
        if not connection_healthy: r.blocks.append("Conexão instável")
        for name, weight in (("adx_fast", 1), ("adx_mid", 2), ("adx_slow", 2)):
            adx = data[name]
            direction = 1 if adx["spread"] > 0 else -1
            if direction > 0: r.call_score += weight; r.reasons_call.append(f"{name} com dominância compradora")
            else: r.put_score += weight; r.reasons_put.append(f"{name} com dominância vendedora")
            if adx["cross"] == direction:
                (r.reasons_call if direction > 0 else r.reasons_put).append(f"{name} apresentou cruzamento")
                if direction > 0: r.call_score += 2
                else: r.put_score += 2
            for key, points in (("expansion", 2), ("slope", 1), ("acceleration", 1)):
                if adx[key] > 0:
                    if direction > 0: r.call_score += points
                    else: r.put_score += points
            if abs(adx["persistence"]) >= 2:
                if direction > 0: r.call_score += 1
                else: r.put_score += 1
        boll = data["bollinger"]
        if boll["state"] == "CONTRACTION": r.call_score -= 3; r.put_score -= 3
        elif boll["direction"] == "BUY_EXPANSION": r.call_score += 3; r.reasons_call.append("Bollinger em expansão compradora")
        elif boll["direction"] == "SELL_EXPANSION": r.put_score += 3; r.reasons_put.append("Bollinger em expansão vendedora")
        mom = data["momentum"]
        if mom["momentum"] > 0: r.call_score += 1 + int(mom["slope"] > 0); r.put_score -= 2
        elif mom["momentum"] < 0: r.put_score += 1 + int(mom["slope"] < 0); r.call_score -= 2
        st = data["supertrend"]["trend"]
        r.call_score += int(st == 1); r.put_score += int(st == -1)
        structure = data["structure"]
        r.call_score += int(structure["higher_low"]) + 2 * int(structure["break_high"])
        r.put_score += int(structure["lower_high"]) + 2 * int(structure["break_low"])
        if data["zigzag"]["provisional"]: r.call_score -= 1; r.put_score -= 1
        r.call_score, r.put_score = max(0, r.call_score), max(0, r.put_score)
        return r


def classify(score: int) -> str:
    if score >= 20: return "VERY_STRONG"
    if score >= 16: return "STRONG"
    if score >= 12: return "MODERATE"
    if score >= 8: return "WEAK"
    return "NO_SIGNAL"
