"""Adaptadores de contratos do ReportOS.

O ReportOS consome os contratos publicos do SESMT a partir deste modulo
local, preservando um ponto unico de adaptacao para reescritas de rotas e
ajustes especificos do ReportOS quando necessario.
"""

from sesmt.contracts import atendimento, flora, himenopteros, manejo

__all__ = ["atendimento", "manejo", "flora", "himenopteros"]
