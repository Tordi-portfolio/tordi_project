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



# from django.shortcuts import render
# import json

# def porosity_view(request):

#     result = None
#     interpretation = []

#     bulk_values = []
#     porosity_values = []

#     if request.method == "POST":

#         # =========================================
#         # MAIN POROSITY CALCULATOR
#         # =========================================

#         if request.POST.get("rho_ma"):

#             rho_ma = float(request.POST.get("rho_ma"))
#             rho_f = float(request.POST.get("rho_f"))
#             rho_b = float(request.POST.get("rho_b"))

#             if rho_ma != rho_f:

#                 if rho_ma == rho_f:
#                     result = "Invalid input: Matrix density cannot equal fluid density."

#                 else:
#                     phi = (rho_ma - rho_b) / (rho_ma - rho_f)
#                     result = round(phi, 4)

#                 if rho_b > rho_ma:
#                     result = "Invalid input: Bulk density cannot be greater than matrix density."

#                 else:
#                     phi = (rho_ma - rho_b) / (rho_ma - rho_f)
#                     result = round(phi, 4)

#                 result = round(phi, 4)

#                 porosity_percent = result * 100

#                 # INTERPRETATION

#                 if rho_ma > rho_b:
#                     interpretation.append(
#                         "Matrix density is greater than bulk density, indicating Significant pore spaces exist, Indicates porosity is present."
#                     )

#                 if rho_b > rho_ma:
#                     interpretation.append(
#                         "Bulk density cannot be greater than matrix density in a normal rock and fluid physics because The pore spaces must contain fluids denser than the rock matrix."
#                     )

#                 if rho_b > rho_f:
#                     interpretation.append(
#                         "Bulk density cannot be greater than fluid, The fluid occupying the pores is lighter than the overall rock."
#                     )

#                 if rho_b < 2.2:
#                     interpretation.append(
#                         "Low bulk density suggests improved reservoir quality and increased pore spaces."
#                     )

#                 if rho_f < 1.0:
#                     interpretation.append(
#                         "Low fluid density may indicate hydrocarbon-bearing formations."
#                     )

#                 if rho_f > rho_ma:
#                     interpretation.append(
#                         "If fluid density is greater than matrix density,the Pore spaces become unusually heavy."
#                     )

#                 if rho_f > rho_b:
#                     interpretation.append(
#                         "If fluid density is greater than bulk density,The fluid inside pores is denser than the average density of the rock."
#                     )

#                 if porosity_percent >= 15:
#                     interpretation.append(
#                         "The formation exhibits good porosity and favorable reservoir characteristics."
#                     )
#             else:
#                 result = "Invalid input: Matrix density cannot equal fluid density."

#         # =========================================
#         # GRAPH DATA
#         # =========================================
#         for i in range(1, 9):
#             porosity = request.POST.get(f"porosity_{i}")
#             bulk = request.POST.get(f"bulk_{i}")

#             if porosity and bulk:

#                 porosity_values.append(float(porosity))
#                 bulk_values.append(float(bulk))
#     context = {
#         "result": result,
#         "interpretation": interpretation,
#         "bulk_values": json.dumps(bulk_values),
#         "porosity_values": json.dumps(porosity_values),
#     }
#     return render(request, "calculate/porosity/porosity.html", context)




from django.shortcuts import render, redirect
import json


def porosity_view(request):

    result = None
    interpretation = []
    bulk_values = []
    porosity_values = []

    # =========================================
    # LOAD SESSION HISTORY (max 3 entries)
    # =========================================
    history = request.session.get('porosity_history', [])

    if request.method == "POST":

        # =========================================
        # MAIN POROSITY CALCULATOR
        # =========================================

        if request.POST.get("rho_ma"):

            rho_ma = float(request.POST.get("rho_ma"))
            rho_f  = float(request.POST.get("rho_f"))
            rho_b  = float(request.POST.get("rho_b"))

            if rho_ma == rho_f:
                result = "Invalid input: Matrix density cannot equal fluid density."

            elif rho_b > rho_ma:
                result = "Invalid input: Bulk density cannot be greater than matrix density."

            else:
                phi = (rho_ma - rho_b) / (rho_ma - rho_f)
                result = round(phi, 4)
                porosity_percent = round(result * 100, 4)

                # =========================================
                # SAVE TO SESSION HISTORY (keep latest 3)
                # =========================================
                entry = {
                    'rho_ma':           rho_ma,
                    'rho_b':            rho_b,
                    'rho_f':            rho_f,
                    'porosity':         result,
                    'porosity_percent': porosity_percent,
                }
                history.append(entry)
                if len(history) > 3:
                    history = history[-3:]   # keep only the newest 3

                request.session['porosity_history'] = history
                request.session.modified = True

                # =========================================
                # INTERPRETATION
                # =========================================
                if rho_ma > rho_b:
                    interpretation.append(
                        "Matrix density is greater than bulk density — significant pore spaces exist, indicating porosity is present."
                    )
                if rho_b > rho_f:
                    interpretation.append(
                        "Bulk density is greater than fluid density — the fluid occupying the pores is lighter than the overall rock."
                    )
                if rho_b < 2.2:
                    interpretation.append(
                        "Low bulk density suggests improved reservoir quality and increased pore spaces."
                    )
                if rho_f < 1.0:
                    interpretation.append(
                        "Low fluid density may indicate hydrocarbon-bearing formations."
                    )
                if rho_f > rho_ma:
                    interpretation.append(
                        "Fluid density is greater than matrix density — pore spaces become unusually heavy."
                    )
                if rho_f > rho_b:
                    interpretation.append(
                        "Fluid density is greater than bulk density — the fluid inside pores is denser than the average density of the rock."
                    )
                if porosity_percent >= 15:
                    interpretation.append(
                        "The formation exhibits good porosity and favorable reservoir characteristics."
                    )

        # =========================================
        # GRAPH DATA (existing Porosity vs Bulk Density plot)
        # =========================================
        for i in range(1, 9):
            porosity_val = request.POST.get(f"porosity_{i}")
            bulk         = request.POST.get(f"bulk_{i}")
            if porosity_val and bulk:
                porosity_values.append(float(porosity_val))
                bulk_values.append(float(bulk))

    # =========================================
    # BUILD CHART DATA FROM SESSION HISTORY
    # Porosity (%) vs Matrix Density
    # =========================================
    history_rho_ma   = [e['rho_ma']          for e in history]
    history_porosity = [e['porosity_percent'] for e in history]

    context = {
        "result":           result,
        "interpretation":   interpretation,
        "bulk_values":      json.dumps(bulk_values),
        "porosity_values":  json.dumps(porosity_values),
        "history":          history,
        "history_rho_ma":   json.dumps(history_rho_ma),
        "history_porosity": json.dumps(history_porosity),
    }

    return render(request, "calculate/porosity/porosity.html", context)


def clear_porosity_history(request):
    """POST-only view: clears the session history and redirects back."""
    if request.method == "POST":
        request.session['porosity_history'] = []
        request.session.modified = True
    return redirect('logs:porosity')   # adjust url name if yours differs



# import json
# from django.shortcuts import render

# def sw_view(request):

#     result = None
#     interpretation = []
#     points = []

#     if request.method == "POST":

#         try:

#             # =========================================
#             # MAIN ARCHIE INPUTS
#             # =========================================

#             a = float(request.POST.get("a", 1))
#             m = float(request.POST.get("m", 2))
#             n = float(request.POST.get("n", 2))
#             rw = float(request.POST.get("rw", 0))
#             rt = float(request.POST.get("rt", 0))
#             phi = float(request.POST.get("phi", 0))

#             # =========================================
#             # VALIDATION
#             # =========================================

#             if phi <= 0 or rt <= 0 or rw <= 0:

#                 result = "Invalid input values."

#             else:

#                 # =========================================
#                 # ARCHIE EQUATION
#                 # =========================================

#                 sw = ((a * rw) / ((phi ** m) * rt)) ** (1 / n)
#                 result = round(sw, 4)

#                 sw_percent = result * 100

#                 # =========================================
#                 # INTERPRETATIONS
#                 # =========================================

#                 # Resistivity
#                 if rt > 50:
#                     interpretation.append(
#                         "High Rt greater than 50 indicates possible hydrocarbon-bearing formation."
#                     )
#                 elif rt < 10:
#                     interpretation.append(
#                         "Low Rt less than 10 suggests water-bearing formation."
#                     )
#                 else:
#                     interpretation.append(
#                         "Moderate Rt indicates mixed fluid saturation."
#                     )

#                 # Porosity
#                 if phi > 0.25:
#                     interpretation.append(
#                         "High porosity greater than 0.25 suggests good reservoir quality."
#                     )
#                 elif phi < 0.10:
#                     interpretation.append(
#                         "Low porosity less than 0.10 suggests tight formation."
#                     )
#                 else:
#                     interpretation.append(
#                         "Moderate porosity greater than 0.10 and less than 0.25 indicates fair reservoir quality."
#                     )

#                 # Water saturation
#                 if sw_percent < 25:
#                     interpretation.append(
#                         "Low Sw less than 25% indicates hydrocarbon rich zone."
#                     )
#                 elif sw_percent <= 50:
#                     interpretation.append(
#                         "Moderate Sw between 25% and 50% indicates mixed fluids."
#                     )
#                 else:
#                     interpretation.append(
#                         "High Sw greater than 50% indicates water-bearing zone."
#                     )

#                 # Tortuosity
#                 if a > 1:
#                     interpretation.append(
#                         "High tortuosity resulting in complex pore paths."
#                     )

#                 if a > m:
#                     interpretation.append(
#                         "When 'a' is greater than 'm', this implies irregular pore geometry or micro-fractures causing detours."
#                     )

#                 if a > n:
#                     interpretation.append(
#                         "When 'a' is greater than 'n', this implies that Hydrocarbons may appear more dominant than they actually are."
#                     )
 
#                 # Cementation
#                 if m > 2:
#                     interpretation.append(
#                         "When 'm' is greater than 2, this implies high cementation resulting in a compact rock."
#                     )

#                 if m > a:
#                     interpretation.append(
#                         "Flow is somewhat easier than expected from rock tightness."
#                     )

#                 if m > n:
#                     interpretation.append(
#                         "Water can still form connected conductive films or channels, Even though pores are tight, water still forms connected conductive paths."
#                     )

#                 # Saturation exponent
#                 if n > 2:
#                     interpretation.append(
#                         "High saturation exponent results in complex fluid distribution."
#                     )

#                 if n > a:
#                     interpretation.append(
#                         "When 'n' is greater than 'a', the flow paths are simple, but water is not continuous in the pores."
#                     )

#                 if n > m:
#                     interpretation.append(
#                         "When 'n' is greater than 'm', the water distribution effect is stronger than pore cementation."
#                     )

#             # =========================================
#             # GRAPH DATA (8 POINT TABLE)
#             # =========================================

#             for i in range(1, 9):

#                 phi_i = request.POST.get(f"phi_{i}")
#                 sw_i = request.POST.get(f"sw_{i}")

#                 if phi_i and sw_i:

#                     try:
#                         points.append({
#                             "x": float(phi_i),   # Porosity (X-axis)
#                             "y": float(sw_i)     # Water saturation (Y-axis)
#                         })
#                     except:
#                         pass

#         except:
#             result = "Invalid input values."

#     # =========================================
#     # CONTEXT
#     # =========================================

#     context = {
#         "result": result,
#         "interpretation": interpretation,
#         "graph_points": json.dumps(points)
#     }

#     return render(request, "calculate/sw/sw.html", context)



import json
from django.shortcuts import render, redirect


def sw_view(request):

    result = None
    interpretation = []
    points = []

    # =========================================
    # LOAD SESSION HISTORY (max 3 entries)
    # =========================================
    history = request.session.get('sw_history', [])

    if request.method == "POST":

        try:

            # =========================================
            # MAIN ARCHIE INPUTS
            # =========================================

            a   = float(request.POST.get("a",   1))
            m   = float(request.POST.get("m",   2))
            n   = float(request.POST.get("n",   2))
            rw  = float(request.POST.get("rw",  0))
            rt  = float(request.POST.get("rt",  0))
            phi = float(request.POST.get("phi", 0))

            # =========================================
            # VALIDATION
            # =========================================

            if phi <= 0 or rt <= 0 or rw <= 0:
                result = "Invalid input values."

            else:

                # =========================================
                # ARCHIE EQUATION
                # Sw = [ (a * Rw) / (phi^m * Rt) ]^(1/n)
                # =========================================

                sw = ((a * rw) / ((phi ** m) * rt)) ** (1 / n)
                result = round(sw, 4)
                sw_percent = result * 100

                # =========================================
                # SAVE TO SESSION HISTORY (keep latest 3)
                # =========================================
                entry = {
                    'a':          a,
                    'm':          m,
                    'n':          n,
                    'rw':         rw,
                    'rt':         rt,
                    'phi':        phi,
                    'sw':         result,
                    'sw_percent': round(sw_percent, 4),
                }
                history.append(entry)
                if len(history) > 3:
                    history = history[-3:]

                request.session['sw_history'] = history
                request.session.modified = True

                # =========================================
                # INTERPRETATIONS
                # =========================================

                # Resistivity
                if rt > 50:
                    interpretation.append(
                        "High Rt (> 50) indicates a possible hydrocarbon-bearing formation."
                    )
                elif rt < 10:
                    interpretation.append(
                        "Low Rt (< 10) suggests a water-bearing formation."
                    )
                else:
                    interpretation.append(
                        "Moderate Rt indicates mixed fluid saturation."
                    )

                # Porosity
                if phi > 0.25:
                    interpretation.append(
                        "High porosity (> 0.25) suggests good reservoir quality."
                    )
                elif phi < 0.10:
                    interpretation.append(
                        "Low porosity (< 0.10) suggests a tight formation."
                    )
                else:
                    interpretation.append(
                        "Moderate porosity (0.10–0.25) indicates fair reservoir quality."
                    )

                # Water saturation
                if sw_percent < 25:
                    interpretation.append(
                        "Low Sw (< 25%) indicates a hydrocarbon-rich zone."
                    )
                elif sw_percent <= 50:
                    interpretation.append(
                        "Moderate Sw (25–50%) indicates mixed fluids."
                    )
                else:
                    interpretation.append(
                        "High Sw (> 50%) indicates a water-bearing zone."
                    )

                # Tortuosity
                if a > 1:
                    interpretation.append(
                        "High tortuosity — complex pore paths present."
                    )
                if a > m:
                    interpretation.append(
                        "When 'a' > 'm': irregular pore geometry or micro-fractures causing flow detours."
                    )
                if a > n:
                    interpretation.append(
                        "When 'a' > 'n': hydrocarbons may appear more dominant than they actually are."
                    )

                # Cementation
                if m > 2:
                    interpretation.append(
                        "When 'm' > 2: high cementation resulting in a compact rock."
                    )
                if m > a:
                    interpretation.append(
                        "Flow is somewhat easier than expected from rock tightness."
                    )
                if m > n:
                    interpretation.append(
                        "Water can still form connected conductive films even though pores are tight."
                    )

                # Saturation exponent
                if n > 2:
                    interpretation.append(
                        "High saturation exponent — complex fluid distribution present."
                    )
                if n > a:
                    interpretation.append(
                        "When 'n' > 'a': flow paths are simple, but water is not continuous in the pores."
                    )
                if n > m:
                    interpretation.append(
                        "When 'n' > 'm': water distribution effect is stronger than pore cementation."
                    )

            # =========================================
            # GRAPH DATA (8-point manual table)
            # =========================================

            for i in range(1, 9):
                phi_i = request.POST.get(f"phi_{i}")
                sw_i  = request.POST.get(f"sw_{i}")
                if phi_i and sw_i:
                    try:
                        points.append({
                            "x": float(phi_i),
                            "y": float(sw_i)
                        })
                    except Exception:
                        pass

        except Exception:
            result = "Invalid input values."

    # =========================================
    # BUILD HISTORY CHART DATA
    # Sw (%) vs Porosity (φ) from session
    # =========================================
    history_phi = [e['phi']        for e in history]
    history_sw  = [e['sw_percent'] for e in history]

    context = {
        "result":         result,
        "interpretation": interpretation,
        "graph_points":   json.dumps(points),
        "history":        history,
        "history_phi":    json.dumps(history_phi),
        "history_sw":     json.dumps(history_sw),
    }

    return render(request, "calculate/sw/sw.html", context)


def clear_sw_history(request):
    """POST-only: clears sw session history and redirects back."""
    if request.method == "POST":
        request.session['sw_history'] = []
        request.session.modified = True
    return redirect('logs:sw')


import math
from django.shortcuts import render


def safe_float(value):
    """Prevents ValueError from empty inputs"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# def perm_view(request):

#     result = None
#     interpretation = []

#     empirical_points = []
#     darcy_points = []

#     # ==========================================
#     # POST HANDLING
#     # ==========================================
#     if request.method == "POST":

#         method = request.POST.get("method")

#         # ==========================================
#         # EMPIRICAL SINGLE CALCULATION
#         # k = C(φ⁴)/(Swi²)
#         # ==========================================
#         if method == "empirical" and "phi_1" not in request.POST:

#             C = safe_float(request.POST.get("C"))
#             phi = safe_float(request.POST.get("phi"))
#             swi = safe_float(request.POST.get("swi"))

#             if None in (C, phi, swi):
#                 result = "Please fill all fields correctly."

#             elif swi == 0:
#                 result = "Swi cannot be zero"

#             else:
#                 k = C * (phi ** 4) / (swi ** 2)
#                 result = f"{round(k,4)} Darcy ({round(k*1000,2)} mD)"

#                 # interpretation
#                 if phi:
#                     if phi > 0.25:
#                         interpretation.append("High porosity increases pore connectivity and permeability.")
#                     elif phi < 0.10:
#                         interpretation.append("Low porosity reduces fluid flow pathways.")

#                 if swi:
#                     if swi > 0.5:
#                         interpretation.append("High water saturation reduces hydrocarbon flow.")

#         # ==========================================
#         # EMPIRICAL GRAPH (k vs φ)
#         # ==========================================
#         elif method == "empirical":

#             C = safe_float(request.POST.get("C")) or 1
#             swi = safe_float(request.POST.get("swi")) or 0.2

#             for i in range(1, 9):
#                 phi = safe_float(request.POST.get(f"phi_{i}"))

#                 if phi is None:
#                     continue

#                 if swi == 0:
#                     continue

#                 k = C * (phi ** 4) / (swi ** 2)

#                 empirical_points.append({
#                     "x": phi,
#                     "y": k
#                 })

#         # ==========================================
#         # DARCY SINGLE CALCULATION
#         # k = (Q μ L) / (A ΔP)
#         # ==========================================
#         elif method == "darcy" and "dP_1" not in request.POST:

#             d = safe_float(request.POST.get("diameter"))
#             L = safe_float(request.POST.get("length"))
#             Q = safe_float(request.POST.get("flow_rate"))
#             mu = safe_float(request.POST.get("viscosity"))
#             dP = safe_float(request.POST.get("pressure_drop"))

#             if None in (d, L, Q, mu, dP):
#                 result = "Please fill all fields correctly."

#             elif dP == 0:
#                 result = "Pressure drop cannot be zero"

#             else:
#                 A = (math.pi * d**2) / 4
#                 k = (Q * mu * L) / (A * dP)

#                 result = f"{round(k,5)} Darcy ({round(k*1000,2)} mD)"

#                 if dP > 10:
#                     interpretation.append("High pressure drop indicates low permeability resistance.")

#                 if Q > 5:
#                     interpretation.append("High flow rate suggests good pore connectivity.")

#         # ==========================================
#         # DARCY GRAPH (k vs ΔP)
#         # ==========================================
#         elif method == "darcy":

#             d = safe_float(request.POST.get("d_1")) or 1
#             L = safe_float(request.POST.get("L_1")) or 10
#             Q = safe_float(request.POST.get("Q_1")) or 1
#             mu = safe_float(request.POST.get("mu_1")) or 1

#             for i in range(1, 9):

#                 dP = safe_float(request.POST.get(f"dP_{i}"))

#                 if dP is None or dP == 0:
#                     continue

#                 A = (math.pi * d**2) / 4
#                 k = (Q * mu * L) / (A * dP)

#                 darcy_points.append({
#                     "x": dP,
#                     "y": k
#                 })

#     return render(request, "calculate/perm/permeability.html", {
#         "result": result,
#         "interpretation": interpretation,
#         "empirical_points": empirical_points,
#         "darcy_points": darcy_points,
#     })


import json
import math
from django.shortcuts import render, redirect


def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def perm_view(request):

    result = None
    interpretation = []
    empirical_points = []
    darcy_points = []
    active_method = "empirical"   # default tab shown on GET

    # ==========================================
    # LOAD SESSION HISTORIES
    # ==========================================
    emp_history   = request.session.get('perm_emp_history',   [])
    darcy_history = request.session.get('perm_darcy_history', [])

    if request.method == "POST":

        method = request.POST.get("method")
        active_method = method or "empirical"

        # ==========================================
        # EMPIRICAL SINGLE CALCULATION
        # k = C * (φ^4) / (Swi^2)
        # ==========================================
        if method == "empirical" and "phi_1" not in request.POST:

            C   = safe_float(request.POST.get("C"))
            phi = safe_float(request.POST.get("phi"))
            swi = safe_float(request.POST.get("swi"))

            if None in (C, phi, swi):
                result = "Please fill all fields correctly."

            elif swi == 0:
                result = "Swi cannot be zero."

            else:
                k = C * (phi ** 4) / (swi ** 2)
                k_md = round(k * 1000, 2)
                k_d  = round(k, 6)
                result = f"{k_d} Darcy ({k_md} mD)"

                # -- session history --
                entry = {
                    'C': C, 'phi': phi, 'swi': swi,
                    'k_darcy': k_d, 'k_md': k_md,
                }
                emp_history.append(entry)
                if len(emp_history) > 3:
                    emp_history = emp_history[-3:]
                request.session['perm_emp_history'] = emp_history
                request.session.modified = True

                # interpretation
                if phi > 0.25:
                    interpretation.append("High porosity (> 0.25) increases pore connectivity and permeability.")
                elif phi < 0.10:
                    interpretation.append("Low porosity (< 0.10) reduces fluid flow pathways.")
                else:
                    interpretation.append("Moderate porosity — fair pore connectivity.")

                if swi > 0.5:
                    interpretation.append("High irreducible water saturation reduces effective hydrocarbon flow.")
                elif swi < 0.2:
                    interpretation.append("Low Swi indicates good hydrocarbon storage potential.")

                if k_md > 100:
                    interpretation.append("Excellent permeability (> 100 mD) — high-flow reservoir.")
                elif k_md > 10:
                    interpretation.append("Good permeability (10–100 mD) — productive reservoir.")
                elif k_md > 1:
                    interpretation.append("Fair permeability (1–10 mD) — may need stimulation.")
                else:
                    interpretation.append("Tight rock (< 1 mD) — low natural flow capacity.")

        # ==========================================
        # EMPIRICAL GRAPH (k vs φ)
        # ==========================================
        elif method == "empirical":

            C   = safe_float(request.POST.get("C"))   or 1
            swi = safe_float(request.POST.get("swi")) or 0.2

            for i in range(1, 9):
                phi = safe_float(request.POST.get(f"phi_{i}"))
                if phi is None or swi == 0:
                    continue
                k = C * (phi ** 4) / (swi ** 2)
                empirical_points.append({"x": phi, "y": round(k, 6)})

        # ==========================================
        # DARCY SINGLE CALCULATION
        # k = (Q * μ * L) / (A * ΔP)
        # ==========================================
        elif method == "darcy" and "dP_1" not in request.POST:

            d   = safe_float(request.POST.get("diameter"))
            L   = safe_float(request.POST.get("length"))
            Q   = safe_float(request.POST.get("flow_rate"))
            mu  = safe_float(request.POST.get("viscosity"))
            dP  = safe_float(request.POST.get("pressure_drop"))

            if None in (d, L, Q, mu, dP):
                result = "Please fill all fields correctly."

            elif dP == 0:
                result = "Pressure drop cannot be zero."

            else:
                A   = (math.pi * d ** 2) / 4
                k   = (Q * mu * L) / (A * dP)
                k_d  = round(k, 6)
                k_md = round(k * 1000, 2)
                result = f"{k_d} Darcy ({k_md} mD)"

                # -- session history --
                entry = {
                    'diameter': d, 'length': L,
                    'flow_rate': Q, 'viscosity': mu,
                    'pressure_drop': dP,
                    'k_darcy': k_d, 'k_md': k_md,
                }
                darcy_history.append(entry)
                if len(darcy_history) > 3:
                    darcy_history = darcy_history[-3:]
                request.session['perm_darcy_history'] = darcy_history
                request.session.modified = True

                if dP > 10:
                    interpretation.append("High pressure drop (> 10 atm) indicates significant flow resistance.")
                elif dP < 2:
                    interpretation.append("Low pressure drop — fluid moves easily through the core.")

                if Q > 5:
                    interpretation.append("High flow rate suggests good pore connectivity.")
                elif Q < 1:
                    interpretation.append("Low flow rate — restricted fluid movement through the core.")

                if k_md > 100:
                    interpretation.append("Excellent permeability (> 100 mD) — high-flow reservoir.")
                elif k_md > 10:
                    interpretation.append("Good permeability (10–100 mD) — productive reservoir.")
                elif k_md > 1:
                    interpretation.append("Fair permeability (1–10 mD) — may need stimulation.")
                else:
                    interpretation.append("Tight rock (< 1 mD) — low natural flow capacity.")

        # ==========================================
        # DARCY GRAPH (k vs ΔP)
        # ==========================================
        elif method == "darcy":

            d  = safe_float(request.POST.get("d_1"))  or 1
            L  = safe_float(request.POST.get("L_1"))  or 10
            Q  = safe_float(request.POST.get("Q_1"))  or 1
            mu = safe_float(request.POST.get("mu_1")) or 1

            for i in range(1, 9):
                dP = safe_float(request.POST.get(f"dP_{i}"))
                if dP is None or dP == 0:
                    continue
                A = (math.pi * d ** 2) / 4
                k = (Q * mu * L) / (A * dP)
                darcy_points.append({"x": dP, "y": round(k, 6)})

    # ==========================================
    # HISTORY CHART DATA
    # ==========================================
    emp_phi_hist = [e['phi']     for e in emp_history]
    emp_k_hist   = [e['k_md']   for e in emp_history]

    darcy_dp_hist = [e['pressure_drop'] for e in darcy_history]
    darcy_k_hist  = [e['k_md']          for e in darcy_history]

    return render(request, "calculate/perm/permeability.html", {
        "result":           result,
        "interpretation":   interpretation,
        "empirical_points": json.dumps(empirical_points),
        "darcy_points":     json.dumps(darcy_points),
        "active_method":    active_method,
        # empirical history
        "emp_history":      emp_history,
        "emp_phi_hist":     json.dumps(emp_phi_hist),
        "emp_k_hist":       json.dumps(emp_k_hist),
        # darcy history
        "darcy_history":    darcy_history,
        "darcy_dp_hist":    json.dumps(darcy_dp_hist),
        "darcy_k_hist":     json.dumps(darcy_k_hist),
    })


def clear_perm_history(request):
    if request.method == "POST":
        which = request.POST.get("which", "both")
        if which in ("empirical", "both"):
            request.session['perm_emp_history'] = []
        if which in ("darcy", "both"):
            request.session['perm_darcy_history'] = []
        request.session.modified = True
    return redirect('logs:perm')

def testing(request):
    return render(request, 'testing/testing.html')