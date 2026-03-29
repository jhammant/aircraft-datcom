"""
Command-line interface for PyDATCOM.

Provides three subcommands:

* ``pydatcom run <input.dat>``   -- parse a classic DATCOM input file and
  run the subsonic analysis pipeline, printing results to stdout.
* ``pydatcom atmos <altitude_ft>`` -- print standard-atmosphere properties.
* ``pydatcom parse <input.dat>``  -- parse and dump namelist contents as JSON.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from pydatcom import __version__


def _cmd_atmos(args: argparse.Namespace) -> None:
    """Print standard-atmosphere properties at a given altitude."""
    from pydatcom.atmosphere import standard_atmosphere

    atm = standard_atmosphere(args.altitude)
    print(f"US Standard Atmosphere 1962 at Z = {atm.altitude:.1f} ft")
    print(f"  Temperature       : {atm.temperature:12.4f} deg R  ({atm.temperature - 459.67:+.2f} deg F)")
    print(f"  Pressure          : {atm.pressure:12.4f} lb/ft^2")
    print(f"  Density           : {atm.density:12.6e} slugs/ft^3")
    print(f"  Speed of sound    : {atm.speed_of_sound:12.4f} ft/s")
    print(f"  dT/dZ             : {atm.d_t_dz:12.6e} deg R/ft")
    print(f"  dP/dZ             : {atm.d_p_dz:12.6e} lb/ft^3")
    print(f"  (1/rho)(drho/dZ)  : {atm.d_rho_dz:12.6e} 1/ft")


def _cmd_parse(args: argparse.Namespace) -> None:
    """Parse a DATCOM input file and dump as JSON."""
    from pydatcom.input_parser import parse_datcom_file

    cases = parse_datcom_file(args.input)
    output = []
    for i, case in enumerate(cases):
        entry = {
            "case": i + 1,
            "case_id": case.case_id,
            "dim": case.dim,
            "controls": case.controls,
            "naca": case.naca,
            "namelists": {},
        }
        for nl_name, nl_data in case.namelists.items():
            entry["namelists"][nl_name] = {
                k: v if not isinstance(v, float) or not np.isnan(v) else None
                for k, v in nl_data.items()
            }
        output.append(entry)

    print(json.dumps(output, indent=2, default=_json_default))


def _cmd_run(args: argparse.Namespace) -> None:
    """Run a subsonic analysis from a DATCOM input file."""
    from pydatcom.input_parser import parse_datcom_file
    from pydatcom.flight_condition import flight_condition, reynolds_number
    from pydatcom.geometry import WingGeometry, BodyGeometry
    from pydatcom.lift_slope import compute_lift_slope
    from pydatcom.aero import lift_coefficient, drag_coefficient, body_aero
    from pydatcom.wing_body import wing_body_aero

    cases = parse_datcom_file(args.input)
    if not cases:
        print("No cases found in input file.", file=sys.stderr)
        sys.exit(1)

    for ci, case in enumerate(cases):
        print(f"{'=' * 60}")
        print(f"CASE {ci + 1}: {case.case_id}")
        print(f"{'=' * 60}")

        flt = case.namelists.get("FLTCON", {})
        opt = case.namelists.get("OPTINS", {})
        syn = case.namelists.get("SYNTHS", {})
        wgp = case.namelists.get("WGPLNF", {})
        wgs = case.namelists.get("WGSCHR", {})
        bod = case.namelists.get("BODY", {})

        # Extract Mach and alpha
        mach_val = flt.get("MACH", 0.0)
        if isinstance(mach_val, list):
            mach_val = mach_val[0]
        alphas = flt.get("ALSCHD", [0.0])
        if not isinstance(alphas, list):
            alphas = [alphas]
        alphas = np.array(alphas, dtype=float)

        s_ref = opt.get("SREF", 1.0)
        cbar = opt.get("CBARR", 1.0)

        # Flight condition
        alt_list = flt.get("ALT", 0.0)
        alt = alt_list[0] if isinstance(alt_list, list) else alt_list
        fc = flight_condition(alt, mach_val)
        print(f"\n  Mach = {mach_val:.3f}, Alt = {alt:.0f} ft, q = {fc.dynamic_pressure:.2f} lb/ft^2")

        # Wing (if present)
        if wgp:
            sspn = wgp.get("SSPN", 1.0)
            wing = WingGeometry(
                chord_root=wgp.get("CHRDR", 1.0),
                semi_span_i=wgp.get("SSPNOP", 0.0),
                semi_span_o=wgp.get("SSPNE", sspn),
                total_semi_span=sspn,
                chord_inboard=wgp.get("CHRDBP", wgp.get("CHRDR", 1.0)),
                chord_tip=wgp.get("CHRDTP", 0.0),
                thickness_to_chord=wgs.get("TOVC", 0.12),
                x_max_tc=wgs.get("XOVC", 0.30),
            )
            sweep_deg = wgp.get("SAVSI", 0.0)
            re_mac = reynolds_number(fc, wing.mac_total)

            if mach_val >= 1.0:
                print(f"\n  Wing: AR={wing.aspect_ratio:.2f} (subsonic method not applicable at M={mach_val:.2f})")
            else:
                ls = compute_lift_slope(wing, mach=mach_val, sweep_half_chord_deg=sweep_deg * 0.6)

                print(f"\n  Wing: AR={wing.aspect_ratio:.2f}, CL_alpha={ls.cl_alpha_per_deg:.4f}/deg, CL_max={ls.cl_max:.2f}")

                wl = lift_coefficient(wing, mach=mach_val, cl_alpha_per_rad=ls.cl_alpha_per_rad,
                                      alphas_deg=alphas, cl_max=ls.cl_max,
                                      alpha_cl_max_deg=ls.alpha_cl_max_deg, s_ref=s_ref)
                wd = drag_coefficient(wing, mach=mach_val, reynolds=re_mac,
                                      cl_alpha_per_rad=ls.cl_alpha_per_rad,
                                      alphas_deg=alphas, cl_array=wl.cl, s_ref=s_ref)

                print(f"\n  {'Alpha':>8s}  {'CL':>10s}  {'CD':>10s}")
                print(f"  {'-----':>8s}  {'------':>10s}  {'------':>10s}")
                for a, cl, cd in zip(alphas, wl.cl, wd.cd):
                    print(f"  {a:8.2f}  {cl:10.4f}  {cd:10.5f}")

        # Body (if present)
        if bod:
            x_arr = bod.get("X", [])
            r_arr = bod.get("R", [])
            if isinstance(x_arr, list) and isinstance(r_arr, list) and len(x_arr) > 1:
                x_np = np.array(x_arr, dtype=float)
                r_np = np.array(r_arr, dtype=float)
                s_np = np.pi * r_np ** 2
                p_np = 2.0 * np.pi * r_np
                ds = bod.get("DS", np.pi * r_np[-1] ** 2)
                body = BodyGeometry(x_stations=x_np, cross_sections=s_np,
                                    perimeters=p_np, radii=r_np, base_area=ds)
                re_body = reynolds_number(fc, body.length)
                ba = body_aero(body, mach=mach_val, reynolds=re_body,
                               alphas_deg=alphas, s_ref=s_ref, cbar=cbar)
                print(f"\n  Body: L={body.length:.2f} ft, f={body.fineness_ratio:.1f}, CN_alpha={ba.cn_alpha:.5f}/deg, CD0={ba.cd0:.5f}")

        print()


def _json_default(obj):
    """JSON serialiser for numpy types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, bool):
        return obj
    raise TypeError(f"Not JSON serializable: {type(obj)}")


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``pydatcom`` CLI."""
    parser = argparse.ArgumentParser(
        prog="pydatcom",
        description="PyDATCOM -- Python USAF Digital DATCOM aerodynamic estimator",
    )
    parser.add_argument("--version", action="version", version=f"pydatcom {__version__}")
    sub = parser.add_subparsers(dest="command")

    # atmos
    p_atmos = sub.add_parser("atmos", help="Print standard-atmosphere properties")
    p_atmos.add_argument("altitude", type=float, help="Geometric altitude in feet")

    # parse
    p_parse = sub.add_parser("parse", help="Parse DATCOM input and dump as JSON")
    p_parse.add_argument("input", help="Path to DATCOM input file")

    # run
    p_run = sub.add_parser("run", help="Run subsonic analysis from DATCOM input")
    p_run.add_argument("input", help="Path to DATCOM input file")

    args = parser.parse_args(argv)

    if args.command == "atmos":
        _cmd_atmos(args)
    elif args.command == "parse":
        _cmd_parse(args)
    elif args.command == "run":
        _cmd_run(args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
