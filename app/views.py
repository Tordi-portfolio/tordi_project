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


# import your Well model from your existing app
# from yourapp.models import Well


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



import numpy as np
from django.shortcuts import render

def porosity_view(request):
    result = None
    bulk_values = []
    porosity_values = []

    if request.method == "POST":
        try:
            rho_ma = float(request.POST.get("rho_ma"))
            rho_f = float(request.POST.get("rho_f"))
            rho_b = float(request.POST.get("rho_b"))

            # Prevent division error
            if rho_ma == rho_f:
                result = "Invalid input (ρma cannot equal ρf)"
            else:
                # Main porosity calculation
                phi = (rho_ma - rho_b) / (rho_ma - rho_f)
                result = round(phi, 4)

                # -------------------------
                # GRAPH DATA
                # -------------------------
                bulk_range = np.linspace(rho_b - 0.3, rho_b + 0.3, 15)

                for b in bulk_range:
                    p = (rho_ma - b) / (rho_ma - rho_f)
                    bulk_values.append(round(b, 3))
                    porosity_values.append(round(p, 4))

        except:
            result = "Invalid input values"

    return render(request, "calculate/porosity.html", {
        "result": result,
        "bulk_values": bulk_values,
        "porosity_values": porosity_values
    })


import numpy as np

def sw_view(request):
    result = None
    phi_values = []
    sw_values = []

    if request.method == "POST":
        a = float(request.POST.get("a"))
        m = float(request.POST.get("m"))
        n = float(request.POST.get("n"))
        rw = float(request.POST.get("rw"))
        rt = float(request.POST.get("rt"))
        phi = float(request.POST.get("phi"))

        # main result
        sw = ((a * rw) / ((phi ** m) * rt)) ** (1 / n)
        result = round(sw, 4)

        # -----------------------------
        # GRAPH DATA: Sw vs Porosity
        # -----------------------------
        phi_range = np.linspace(0.05, 0.35, 20)

        for p in phi_range:
            try:
                sw_g = ((a * rw) / ((p ** m) * rt)) ** (1 / n)
            except:
                sw_g = 0

            phi_values.append(round(p, 3))
            sw_values.append(round(sw_g, 4))

    return render(request, "calculate/sw.html", {
        "result": result,
        "phi_values": phi_values,
        "sw_values": sw_values
    })



import numpy as np
import math
from django.shortcuts import render

def perm_view(request):
    result = None
    method = None

    x_values = []
    k_values = []

    if request.method == "POST":
        method = request.POST.get("method")

        # =========================
        # EMPIRICAL METHOD
        # =========================
        if method == "empirical":
            C = float(request.POST.get("C"))
            phi = float(request.POST.get("phi"))
            swi = float(request.POST.get("swi"))

            if swi != 0:
                k = C * (phi ** 4) / (swi ** 2)
                result = round(k, 6)

                # GRAPH: k vs porosity
                phi_range = np.linspace(0.05, 0.35, 20)

                for p in phi_range:
                    k_val = C * (p ** 4) / (swi ** 2)
                    x_values.append(round(p, 3))
                    k_values.append(round(k_val, 6))

        # =========================
        # DARCY METHOD
        # =========================
        elif method == "darcy":
            d = float(request.POST.get("diameter"))
            L = float(request.POST.get("length"))
            Q = float(request.POST.get("flow_rate"))
            mu = float(request.POST.get("viscosity"))
            dP = float(request.POST.get("pressure_drop"))

            A = (math.pi * d**2) / 4

            if dP != 0:
                k = (Q * mu * L) / (A * dP)
                result = round(k, 6)

                # GRAPH: k vs pressure drop
                dp_range = np.linspace(dP * 0.5, dP * 2, 20)

                for dp in dp_range:
                    k_val = (Q * mu * L) / (A * dp)
                    x_values.append(round(dp, 3))
                    k_values.append(round(k_val, 6))

    return render(request, "calculate/permeability.html", {
        "result": result,
        "method": method,
        "x_values": x_values,
        "k_values": k_values
    })