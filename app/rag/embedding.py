"""임베딩 (embedding) — 로컬 모델만.

청크 → 벡터. 에어갭: 런타임에 외부에서 가중치를 받지 않는다(미리 주입).
모델은 무거우므로 프로세스당 1회만 로드한다(lazy singleton).

운영 포인트:
  - settings.embedding_model: dev=Hub ID("BAAI/bge-m3") / 에어갭=로컬 경로.
    코드는 안 바뀌고 .env(설정) 한 곳만 바꾼다.
  - 에어갭 안전장치 HF_HUB_OFFLINE=1 은 코드가 아니라 컨테이너 env로 주입한다
    (조용히 네트워크 대신 시끄럽게 실패 → 폐쇄망 위반을 빌드 때 잡는다).
"""

from sentence_transformers import SentenceTransformer

from app.config import settings

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """첫 호출에만 로드, 이후 재사용. global 없으면 _model이 지역 취급돼 UnboundLocalError."""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    # encode()는 numpy 배열 반환 → 계약(list[list[float]])·DB·JSON 위해 순수 리스트로.
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()
