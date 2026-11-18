"""Função de divisão usada como exemplo, com um caso de falha demonstrável."""


def divide(a: float, b: float) -> float:
    """Retorna o quociente de ``a`` por ``b``.

    Args:
        a: Dividendo.
        b: Divisor.

    Returns:
        O resultado de ``a / b``.

    Raises:
        ValueError: Se ``b`` for zero.
    """
    if b == 0:
        raise ValueError("O divisor não pode ser zero.")
    return a / b
