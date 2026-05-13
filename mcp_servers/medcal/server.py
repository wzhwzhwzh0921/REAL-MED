"""MedCalc MCP Server — 82 Medical Calculation Tools.

Provides atomic medical calculation formulas as MCP tools
for clinical decision support and benchmarking.

Usage:
    python -m medcal.server
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "medcal",
    instructions=(
        "Medical calculation tools for clinical formulas. "
        "Each tool implements one atomic formula. Chain tools for multi-step calculations. "
        "All outputs include value, unit, formula_used, and optional interpretation/warning."
    ),
)

# Import all domain modules to register tools
from medcal.formulas import renal  # noqa: F401, E402
from medcal.formulas import body_metrics  # noqa: F401, E402
from medcal.formulas import pharmacokinetics  # noqa: F401, E402
from medcal.formulas import vancomycin  # noqa: F401, E402
from medcal.formulas import cardiac  # noqa: F401, E402
from medcal.formulas import hemodynamics  # noqa: F401, E402
from medcal.formulas import respiratory  # noqa: F401, E402
from medcal.formulas import acid_base  # noqa: F401, E402
from medcal.formulas import osmolality  # noqa: F401, E402
from medcal.formulas import fluid_electrolyte  # noqa: F401, E402
from medcal.formulas import hepatology  # noqa: F401, E402
from medcal.formulas import valvular  # noqa: F401, E402
from medcal.formulas import echocardiography  # noqa: F401, E402
from medcal.formulas import burn  # noqa: F401, E402
from medcal.formulas import endocrine  # noqa: F401, E402
from medcal.formulas import toxicology  # noqa: F401, E402
from medcal.formulas import oncology  # noqa: F401, E402
from medcal.formulas import neurology  # noqa: F401, E402
from medcal.formulas import dialysis  # noqa: F401, E402
from medcal.formulas import nutrition  # noqa: F401, E402
from medcal.formulas import hematology  # noqa: F401, E402
from medcal.formulas import nuclear_medicine  # noqa: F401, E402
from medcal.formulas import diuretics  # noqa: F401, E402


def main():
    """Run the MedCalc MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
