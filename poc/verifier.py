import json
import math
from pathlib import Path


# Демонстрационные пороги PoC.
# В целевой системе они должны выбираться на validation set.
QUALITY_MIN = 0.60
LIVENESS_MIN = 0.80
ALLOW_MATCH_MIN = 0.80
MANUAL_REVIEW_MATCH_MIN = 0.60
MIN_MARGIN = 0.10


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))

    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


class AccessVerifier:

    def __init__(self, employees_path, audit_log_path):
        self.employees_path = Path(employees_path)
        self.audit_log_path = Path(audit_log_path)

        with self.employees_path.open(
            "r",
            encoding="utf-8"
        ) as file:
            self.employees = json.load(file)

    def search_employee(self, query_embedding):

        candidates = []

        for employee in self.employees:

            score = cosine_similarity(
                query_embedding,
                employee["embedding"]
            )

            candidates.append(
                (score, employee)
            )

        candidates.sort(
            key=lambda item: item[0],
            reverse=True
        )

        best_score, best_employee = candidates[0]

        if len(candidates) > 1:
            second_score = candidates[1][0]
        else:
            second_score = -1.0

        return {
            "employee": best_employee,
            "match_score": best_score,
            "margin_to_second_best":
                best_score - second_score
        }

    def write_audit_log(self, result):

        self.audit_log_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with self.audit_log_path.open(
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                json.dumps(
                    result,
                    ensure_ascii=False
                )
                + "\n"
            )

    def verify(self, event):

        mock = event["mock"]

        result = {
            "event_id": event["event_id"],
            "gate_id": event["gate_id"],
            "camera_id": event["camera_id"],

            "decision": None,
            "employee_id": None,

            "match_score": None,
            "margin_to_second_best": None,

            "quality": {
                "face_detected":
                    mock["face_detected"],

                "quality_score":
                    mock["quality_score"],

                "liveness_score":
                    mock["liveness_score"]
            },

            "reasons": [],

            "turnstile_command": None,

            "requires_human_review": False
        }

        # 1. Проверяем наличие лица

        if not mock["face_detected"]:

            result["decision"] = "manual_review"

            result[
                "requires_human_review"
            ] = True

            result["reasons"].append(
                "face_not_detected"
            )

            self.write_audit_log(result)

            return result

        # 2. Проверяем качество кадра

        if mock["quality_score"] < QUALITY_MIN:

            result["decision"] = "manual_review"

            result[
                "requires_human_review"
            ] = True

            result["reasons"].append(
                "low_quality"
            )

            self.write_audit_log(result)

            return result

        # 3. Проверяем liveness

        if mock["liveness_score"] < LIVENESS_MIN:

            result["decision"] = "manual_review"

            result[
                "requires_human_review"
            ] = True

            result["reasons"].append(
                "liveness_failed"
            )

            self.write_audit_log(result)

            return result

        # 4. Ищем сотрудника

        search_result = self.search_employee(
            mock["embedding"]
        )

        employee = search_result["employee"]

        score = search_result["match_score"]

        margin = search_result[
            "margin_to_second_best"
        ]

        result["employee_id"] = employee[
            "employee_id"
        ]

        result["match_score"] = round(
            score,
            4
        )

        result[
            "margin_to_second_best"
        ] = round(
            margin,
            4
        )

        # 5. Проверяем права доступа

        if not employee["access_allowed"]:

            result["decision"] = "deny"

            result["reasons"].append(
                "employee_access_denied"
            )

        # 6. Уверенное совпадение

        elif (
            score >= ALLOW_MATCH_MIN
            and margin >= MIN_MARGIN
        ):

            result["decision"] = "allow"

            result[
                "turnstile_command"
            ] = "open"

            result["reasons"].extend([
                "quality_ok",
                "liveness_ok",
                "match_above_allow_threshold",
                "margin_ok"
            ])

        # 7. Сомнительное совпадение

        elif (
            score
            >= MANUAL_REVIEW_MATCH_MIN
        ):

            result[
                "decision"
            ] = "manual_review"

            result[
                "requires_human_review"
            ] = True

            result["reasons"].append(
                "low_match_confidence"
            )

        # 8. Надёжного совпадения нет

        else:

            result["decision"] = "deny"

            result["reasons"].append(
                "no_reliable_match"
            )

        # 9. Записываем решение

        self.write_audit_log(result)

        return result