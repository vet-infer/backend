import os
import sys
from datetime import datetime, timezone

import httpx


BASE_URL = os.getenv("TEST_BASE_URL")
LOGIN_EMAIL = os.getenv("TEST_LOGIN_EMAIL")
LOGIN_PASSWORD = os.getenv("TEST_LOGIN_PASSWORD")


class E2ERunner:
    def __init__(self) -> None:
        if not BASE_URL:
            raise RuntimeError("Configura TEST_BASE_URL para ejecutar el flujo e2e.")
        self.client = httpx.Client(base_url=BASE_URL, timeout=15.0)
        self.token: str | None = None
        self.owner_id: int | None = None
        self.patient_id: int | None = None
        self.evaluation_id: int | None = None
        self.result_id: int | None = None
        self.disease_id: int | None = None
        self.passed = 0
        self.failed = 0

    @property
    def auth_headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        print(f"[{status}] {name}{' - ' + detail if detail else ''}")
        if condition:
            self.passed += 1
        else:
            self.failed += 1

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        response = self.client.request(method, path, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            print(f"\n[ERROR] {method} {path} -> {response.status_code}")
            print(response.text)
            raise
        return response

    def login(self) -> None:
        if not LOGIN_EMAIL or not LOGIN_PASSWORD:
            raise RuntimeError("Configura TEST_LOGIN_EMAIL y TEST_LOGIN_PASSWORD para ejecutar el flujo e2e.")
        response = self.request(
            "POST",
            "/api/v1/auth/login",
            json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
        )
        data = response.json()
        self.token = data.get("access_token")
        self.check("Login JWT", response.status_code == 200 and bool(self.token))

    def fetch_catalogs(self) -> tuple[int, int, int]:
        species = self.request("GET", "/api/v1/species", headers=self.auth_headers).json()
        dog = next(item for item in species if item["name"].lower() == "perro")
        breeds = self.request(
            "GET",
            f"/api/v1/breeds?species_id={dog['id']}",
            headers=self.auth_headers,
        ).json()
        breed = next(item for item in breeds if item["name"].lower() == "poodle")
        diseases = self.request("GET", "/api/v1/diseases", headers=self.auth_headers).json()
        diabetes = next(
            item
            for item in diseases
            if item["name"].lower() == "diabetes mellitus" and item["species_id"] == dog["id"]
        )
        self.disease_id = diabetes["id"]
        self.check("Catalogos base", bool(dog and breed and diabetes), f"species={dog['id']} breed={breed['id']} disease={diabetes['id']}")
        return dog["id"], breed["id"], diabetes["id"]

    def create_owner(self) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        response = self.request(
            "POST",
            "/api/v1/owners/",
            json={
                "first_name": "Elena",
                "last_name": f"Paso6-{stamp}",
                "phone": "+51999000666",
                "email": f"paso6.owner.{stamp}@example.com",
                "address": "Av. Validacion OE3 123",
            },
        )
        data = response.json()
        self.owner_id = data["id"]
        self.check("Crear owner", response.status_code == 201 and self.owner_id is not None, f"owner_id={self.owner_id}")

        fetched = self.request("GET", f"/api/v1/owners/{self.owner_id}").json()
        self.check("Consultar owner", fetched["id"] == self.owner_id)

    def create_patient(self, species_id: int, breed_id: int) -> None:
        response = self.request(
            "POST",
            "/api/v1/patients",
            headers=self.auth_headers,
            json={
                "owner_id": self.owner_id,
                "name": "Max Paso6",
                "species_id": species_id,
                "breed_id": breed_id,
                "sex": "Macho",
                "birth_date": "2016-05-20",
                "weight": 18.4,
            },
        )
        data = response.json()
        self.patient_id = data["id"]
        ok = (
            response.status_code == 201
            and data["owner"]["id"] == self.owner_id
            and data["species"]["id"] == species_id
            and data["breed"]["id"] == breed_id
        )
        self.check("Crear patient asociado", ok, f"patient_id={self.patient_id}")

        fetched = self.request("GET", f"/api/v1/patients/{self.patient_id}", headers=self.auth_headers).json()
        self.check("Consultar patient", fetched["id"] == self.patient_id)

    def create_evaluation(self) -> None:
        response = self.request(
            "POST",
            "/api/v1/evaluations",
            headers=self.auth_headers,
            json={
                "patient_id": self.patient_id,
                "reason": "Poliuria, polidipsia y sospecha de diabetes mellitus",
                "observations": "Caso E2E Paso 6 OE3: paciente canino adulto con signos metabolicos.",
                "facts": [
                    {"fact_key": "poliuria", "value": True, "source_type": "symptom"},
                    {"fact_key": "polidipsia", "value": True, "source_type": "symptom"},
                    {"fact_key": "polifagia", "value": True, "source_type": "symptom"},
                    {"fact_key": "perdida de peso", "value": True, "source_type": "symptom"},
                    {"fact_key": "glucosa", "value": 280.0, "source_type": "clinical_variable"},
                    {"fact_key": "glucosuria", "value": "presente", "source_type": "clinical_variable"},
                ],
            },
        )
        data = response.json()
        self.evaluation_id = data["id"]
        self.check("Crear evaluation con facts", response.status_code == 201 and len(data["facts"]) == 6, f"evaluation_id={self.evaluation_id}")

    def process_inference(self) -> None:
        response = self.request(
            "POST",
            f"/api/v1/evaluaciones/{self.evaluation_id}/procesar",
            headers=self.auth_headers,
        )
        data = response.json()
        diabetes = next((item for item in data["resultados"] if item["enfermedad"] == "Diabetes mellitus"), None)
        ok = (
            response.status_code == 200
            and data["metodo_inferencia"] == "reglas_bayes"
            and diabetes is not None
            and diabetes["nivel_riesgo"] == "Alto"
            and diabetes["probabilidad"] is not None
            and diabetes["probabilidad"] >= 0.50
            and {"DM-R03", "DM-R04"}.issubset(set(diabetes["reglas_activadas"]))
        )
        self.check(
            "Procesar inferencia reglas + Bayes",
            ok,
            f"DM prob={diabetes['probabilidad'] if diabetes else None} risk={diabetes['nivel_riesgo'] if diabetes else None}",
        )

    def consult_results(self) -> None:
        results = self.request(
            "GET",
            f"/api/v1/evaluations/{self.evaluation_id}/results",
            headers=self.auth_headers,
        ).json()
        diabetes = next((item for item in results if item["disease_id"] == self.disease_id), None)
        self.result_id = diabetes["id"] if diabetes else None
        ok = (
            diabetes is not None
            and diabetes["probability"] is not None
            and diabetes["inference_method"] == "reglas_bayes"
            and diabetes["risk_level"] == "Alto"
            and diabetes["risk_level_id"] is not None
        )
        self.check("Consultar resultados persistidos", ok, f"result_id={self.result_id}")

        activated = self.request(
            "GET",
            f"/api/v1/results/{self.result_id}/activated-rules",
            headers=self.auth_headers,
        ).json()
        self.check("Consultar reglas activadas", len(activated) >= 2)

    def consult_history(self) -> None:
        history = self.request(
            "GET",
            f"/api/v1/patients/{self.patient_id}/history",
            headers=self.auth_headers,
        ).json()
        event_types = {item["event_type"] for item in history}
        self.check(
            "Consultar historial clinico",
            {"clinical_evaluation", "inference_result"}.issubset(event_types),
            f"events={sorted(event_types)}",
        )

    def run(self) -> int:
        self.login()
        species_id, breed_id, _ = self.fetch_catalogs()
        self.create_owner()
        self.create_patient(species_id, breed_id)
        self.create_evaluation()
        self.process_inference()
        self.consult_results()
        self.consult_history()
        total = self.passed + self.failed
        percent = (self.passed / total * 100) if total else 0
        print("\n=== RESUMEN E2E PASO 6 ===")
        print(f"Checks aprobados: {self.passed}")
        print(f"Checks fallidos : {self.failed}")
        print(f"Exito           : {percent:.2f}%")
        return 0 if self.failed == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(E2ERunner().run())
    except Exception as exc:
        print(f"\n[FAIL] Flujo E2E interrumpido: {exc}")
        sys.exit(1)
