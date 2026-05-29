import json
import pandas as pd
import lasio
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from .forms import UploadLASForm
from .models import UploadedLAS
from django.contrib import messages

def index(request):
    return render(request, 'logs/index.html')

def porosity_details(request):
    return render(request, 'calculate/porosity/porosity_details.html')

def perm_details(request):
    return render(request, 'calculate/perm/perm_details.html')

def sw_details(request):
    return render(request, 'calculate/sw/sw_details.html')


def _read_las_from_storage(file_field):
    """Read LAS file from UploadedLAS.file and return (lasio.LASFile, DataFrame)."""
    fpath = file_field.path
    las = lasio.read(fpath, ignore_data=False, read_policy="default")
    df = las.df()  # Depth/index becomes DataFrame index
    if df.index.name is None:
        df.index.name = las.index_unit or "INDEX"
    return las, df


@require_http_methods(["GET", "POST"])
def home(request):
    """Upload LAS file and redirect to viewer."""
    form = UploadLASForm()
    if request.method == "POST":
        form = UploadLASForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            messages.success(request, 'You can now view your las file datas')
            return redirect("logs:view_las", pk=obj.pk)
    return render(request, "logs/home.html", {"form": form})


def view_las(request, pk: int):
    """Display LAS metadata and curves list."""
    obj = get_object_or_404(UploadedLAS, pk=pk)
    try:
        las, df = _read_las_from_storage(obj.file)
    except Exception as e:
        return render(request, "logs/error.html", {"error": str(e)})

    well_info = {item.mnemonic: str(item.value) for item in las.well}
    params = {item.mnemonic: str(item.value) for item in las.params}

    curves = []
    index_name = df.index.name or "INDEX"

    for c in las.curves:
        # Check if this curve is actually the DataFrame index
        if c.mnemonic == index_name:
            col_data = pd.Series(df.index)
        elif c.mnemonic in df.columns:
            col_data = df[c.mnemonic]
        else:
            # Skip missing curve
            continue

        curves.append({
            "mnemonic": c.mnemonic,
            "unit": c.unit or "",
            "descr": c.descr or "",
            "min": float(pd.to_numeric(col_data, errors="coerce").min()),
            "max": float(pd.to_numeric(col_data, errors="coerce").max()),
            "null": las.null if hasattr(las, "null") else None,
        })

    context = {
        "obj": obj,
        "well_info": well_info,
        "params": params,
        "curves": curves,
        "index_label": index_name,
    }
    return render(request, "logs/view.html", context)


def curve_api(request, pk: int, curve_mnemonic: str):
    """Return JSON curve data for Plotly chart."""
    obj = get_object_or_404(UploadedLAS, pk=pk)
    try:
        las, df = _read_las_from_storage(obj.file)
    except Exception:
        raise Http404("LAS could not be read")

    index_name = df.index.name or "INDEX"

    if curve_mnemonic == index_name:
        series = pd.Series(df.index)
    elif curve_mnemonic in df.columns:
        series = df[curve_mnemonic]
    else:
        raise Http404("Curve not found")

    idx = df.index

    # Downsample for speed
    max_points = 5000
    if len(series) > max_points:
        step = len(series) // max_points
        series = series[::step]
        idx = idx[::step]

    data = {
        "index_label": index_name,
        "curve": curve_mnemonic,
        "x": idx.astype(float).tolist(),   # depth/index
        "y": pd.to_numeric(series, errors="coerce").astype(float).tolist(),
    }
    return JsonResponse(data)


def tordi(request):
    return render(request, 'tordi.html')

def parameter(request):
    return render(request, 'parameter.html')


def analysis_home(request):
    result = None

    if request.method == "POST":
        # -------------------------
        # INPUT VALUES FROM FORM
        # -------------------------
        rho_ma = float(request.POST.get("rho_ma"))
        rho_f = float(request.POST.get("rho_f"))
        rho_b = float(request.POST.get("rho_b"))

        a = float(request.POST.get("a"))
        m = float(request.POST.get("m"))
        n = float(request.POST.get("n"))
        rw = float(request.POST.get("rw"))
        rt = float(request.POST.get("rt"))

        C = float(request.POST.get("C"))
        swi = float(request.POST.get("swi"))

        # -------------------------
        # CALCULATIONS
        # -------------------------

        # Porosity
        phi = (rho_ma - rho_b) / (rho_ma - rho_f)

        # Water saturation (Archie)
        sw = ((a * rw) / ((phi ** m) * rt)) ** (1 / n) if phi > 0 else 0

        # Permeability
        perm = C * (phi ** 4) / (swi ** 2)

        result = {
            "phi": round(phi, 4),
            "sw": round(sw, 4),
            "perm": round(perm, 4),
        }

    return render(request, "calculate/analysis.html", {"result": result})



from django.shortcuts import render
import json

def porosity_view(request):

    result = None
    interpretation = []

    bulk_values = []
    porosity_values = []

    if request.method == "POST":

        # =========================================
        # MAIN POROSITY CALCULATOR
        # =========================================

        if request.POST.get("rho_ma"):

            rho_ma = float(request.POST.get("rho_ma"))
            rho_f = float(request.POST.get("rho_f"))
            rho_b = float(request.POST.get("rho_b"))

            if rho_ma != rho_f:

                if rho_ma == rho_f:
                    result = "Invalid input: Matrix density cannot equal fluid density."

                else:
                    phi = (rho_ma - rho_b) / (rho_ma - rho_f)
                    result = round(phi, 4)

                result = round(phi, 4)

                porosity_percent = result * 100

                # INTERPRETATION

                if rho_ma > rho_b:
                    interpretation.append(
                        "Matrix density is greater than bulk density, indicating pore spaces within the formation."
                    )

                if rho_b < 2.2:
                    interpretation.append(
                        "Low bulk density suggests improved reservoir quality and increased pore spaces."
                    )

                if rho_f < 1.0:
                    interpretation.append(
                        "Low fluid density may indicate hydrocarbon-bearing formations."
                    )

                if porosity_percent >= 15:
                    interpretation.append(
                        "The formation exhibits good porosity and favorable reservoir characteristics."
                    )
            else:
                result = "Invalid input: Matrix density cannot equal fluid density."

        # =========================================
        # GRAPH DATA
        # =========================================
        for i in range(1, 9):
            porosity = request.POST.get(f"porosity_{i}")
            bulk = request.POST.get(f"bulk_{i}")

            if porosity and bulk:

                porosity_values.append(float(porosity))
                bulk_values.append(float(bulk))
    context = {
        "result": result,
        "interpretation": interpretation,
        "bulk_values": json.dumps(bulk_values),
        "porosity_values": json.dumps(porosity_values),
    }
    return render(request, "calculate/porosity/porosity.html", context)



import json
from django.shortcuts import render

def sw_view(request):

    result = None
    interpretation = []
    points = []

    if request.method == "POST":

        try:

            # =========================================
            # MAIN ARCHIE INPUTS
            # =========================================

            a = float(request.POST.get("a", 1))
            m = float(request.POST.get("m", 2))
            n = float(request.POST.get("n", 2))
            rw = float(request.POST.get("rw", 0))
            rt = float(request.POST.get("rt", 0))
            phi = float(request.POST.get("phi", 0))

            # =========================================
            # VALIDATION
            # =========================================

            if phi <= 0 or rt <= 0 or rw <= 0:

                result = "Invalid input values."

            else:

                # =========================================
                # ARCHIE EQUATION
                # =========================================

                sw = ((a * rw) / ((phi ** m) * rt)) ** (1 / n)
                result = round(sw, 4)

                sw_percent = result * 100

                # =========================================
                # INTERPRETATIONS
                # =========================================

                # Resistivity
                if rt > 50:
                    interpretation.append(
                        "High Rt indicates possible hydrocarbon-bearing formation."
                    )
                elif rt < 10:
                    interpretation.append(
                        "Low Rt suggests water-bearing formation."
                    )
                else:
                    interpretation.append(
                        "Moderate Rt indicates mixed fluid saturation."
                    )

                # Porosity
                if phi > 0.25:
                    interpretation.append(
                        "High porosity → good reservoir quality."
                    )
                elif phi < 0.10:
                    interpretation.append(
                        "Low porosity → tight formation."
                    )
                else:
                    interpretation.append(
                        "Moderate porosity → fair reservoir quality."
                    )

                # Water saturation
                if sw_percent < 25:
                    interpretation.append(
                        "Low Sw → hydrocarbon-rich zone."
                    )
                elif sw_percent <= 50:
                    interpretation.append(
                        "Moderate Sw → mixed fluids."
                    )
                else:
                    interpretation.append(
                        "High Sw → water-bearing zone."
                    )

                # Tortuosity
                if a > 1:
                    interpretation.append(
                        "High tortuosity → complex pore paths."
                    )

                # Cementation
                if m > 2:
                    interpretation.append(
                        "High cementation → compact rock."
                    )

                # Saturation exponent
                if n > 2:
                    interpretation.append(
                        "High saturation exponent → complex fluid distribution."
                    )

            # =========================================
            # GRAPH DATA (8 POINT TABLE)
            # =========================================

            for i in range(1, 9):

                phi_i = request.POST.get(f"phi_{i}")
                sw_i = request.POST.get(f"sw_{i}")

                if phi_i and sw_i:

                    try:
                        points.append({
                            "x": float(phi_i),   # Porosity (X-axis)
                            "y": float(sw_i)     # Water saturation (Y-axis)
                        })
                    except:
                        pass

        except:
            result = "Invalid input values."

    # =========================================
    # CONTEXT
    # =========================================

    context = {
        "result": result,
        "interpretation": interpretation,
        "graph_points": json.dumps(points)
    }

    return render(request, "calculate/sw/sw.html", context)



import math
from django.shortcuts import render

def perm_view(request):
    result = None
    method = None

    if request.method == "POST":
        method = request.POST.get("method")

        # -------------------------
        # EMPIRICAL METHOD
        # -------------------------
        if method == "empirical":
            C = float(request.POST.get("C"))
            phi = float(request.POST.get("phi"))
            swi = float(request.POST.get("swi"))

            if swi == 0:
                result = "Invalid Swi (cannot be zero)"
            else:
                k = C * (phi ** 4) / (swi ** 2)
                result = f"{round(k,4)} Darcy ({round(k*1000,2)} mD)"

        # -------------------------
        # DARCY METHOD
        # -------------------------
        elif method == "darcy":
            d = float(request.POST.get("diameter"))
            L = float(request.POST.get("length"))
            Q = float(request.POST.get("flow_rate"))
            mu = float(request.POST.get("viscosity"))
            dP = float(request.POST.get("pressure_drop"))

            A = (math.pi * d**2) / 4

            if dP == 0:
                result = "Pressure drop cannot be zero"
            else:
                k = (Q * mu * L) / (A * dP)
                result = f"{round(k,5)} Darcy ({round(k*1000,2)} mD)"

    return render(request, "calculate/perm/permeability.html", {
        "result": result,
        "method": method
    })


def testing(request):
    return render(request, 'testing/testing.html')