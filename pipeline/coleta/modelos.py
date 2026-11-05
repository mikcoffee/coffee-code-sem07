"""Os dados limpos: um molde para cada tipo de coisa que coletamos."""
import hashlib
import json
from dataclasses import dataclass, field


def _hash(conteudo: dict) -> str:
    texto = json.dumps(conteudo, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


@dataclass
class Vaga:
    fonte: str
    id_externo: str
    titulo: str
    url: str
    empresa: str | None = None
    cidade: str | None = None
    uf: str | None = None
    modalidade: str | None = None
    nivel: str | None = None
    salario_min: int | None = None
    salario_max: int | None = None
    publicada: str | None = None
    tags: list[str] = field(default_factory=list)
    descricao: str | None = None
    # campos que não deu para ler hoje (diferente de "a página não tem")
    indisponiveis: tuple[str, ...] = ()

    def como_linha(self) -> dict:
        linha = {k: v for k, v in self.__dict__.items()
                 if k not in ("fonte", "id_externo", "indisponiveis")}
        linha["tags"] = ",".join(self.tags)
        return linha

    def conteudo_hash(self) -> str:
        return _hash(self.como_linha())


@dataclass
class Evento:
    fonte: str
    id_externo: str
    titulo: str
    url: str
    inicio: str | None = None
    local: str | None = None
    online: int = 0
    preco_centavos: int | None = None
    preco_estudante_centavos: int | None = None
    organizacao: str | None = None

    def como_linha(self) -> dict:
        return {k: v for k, v in self.__dict__.items()
                if k not in ("fonte", "id_externo")}

    def conteudo_hash(self) -> str:
        return _hash(self.como_linha())
