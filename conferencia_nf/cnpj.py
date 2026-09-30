"""Dígito verificador de CNPJ: checagem determinística que pega leitura errada de graça."""

_PESOS_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PESOS_2 = [6, *_PESOS_1]


def _dv(digitos: str, pesos: list[int]) -> str:
    resto = sum(int(d) * p for d, p in zip(digitos, pesos)) % 11
    return "0" if resto < 2 else str(11 - resto)


def completar(base12: str) -> str:
    """Recebe os 12 primeiros dígitos e devolve o CNPJ com os 2 verificadores."""
    d1 = _dv(base12, _PESOS_1)
    return base12 + d1 + _dv(base12 + d1, _PESOS_2)


def valido(cnpj: str) -> bool:
    return len(cnpj) == 14 and cnpj.isdigit() and completar(cnpj[:12]) == cnpj


def formatar(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
