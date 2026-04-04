# Digital DATCOM - Python + Rust Implementation

**Heritage aerospace software (1960s-80s) with modern Python and Rust implementations**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Rust](https://img.shields.io/badge/Rust-1.70+-orange.svg)](https://rust-lang.org)
[![License](https://img.shields.io/badge/License-Public%20Domain-green.svg)](LICENSE)
[![WebAssembly](https://img.shields.io/badge/WebAssembly-Ready-orange.svg)](https://webassembly.org)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Try%20Now-brightgreen.svg)](https://jhammant.github.io/datcom/)

## 🚀 Live Demo

**Try it now in your browser:** [https://jhammant.github.io/datcom/](https://jhammant.github.io/datcom/)

Real-time aerospace analysis with heritage algorithms running in WebAssembly.

## What is Digital DATCOM?

Digital DATCOM (Data Compendium) is the legendary USAF aerospace analysis software that powered the design of Apollo, Space Shuttle, F-16, and countless other aircraft. Originally developed in the 1960s-80s, it contains 553,000+ lines of validated Fortran algorithms representing decades of wind tunnel testing and flight validation.

With Artemis returning humans to the Moon, these heritage algorithms should be accessible to the next generation of aerospace engineers.

## 🏛️ Heritage Code Archaeology

Digging through the original codebase reveals fascinating historical artifacts:

- **NASA references**: Comments contain "NASA TM-84639" and "NASA TN D-176" technical memoranda
- **Wright Patterson AFB**: 1970s contact information still embedded in source files  
- **Cryptic algorithm names**: `HYPBOD` (hypersonic body), `SUPLTG` (supersonic lifting), `AGENR` (general aero) - limited by 6-character Fortran constraints
- **Slide rule era math**: Mathematical constants hardcoded to precision limits of the time

## ⚡ Performance & Accessibility

### Honest Performance Claims
- **Python implementation**: ~1-10ms for typical aerodynamic calculations
- **Rust implementation**: ~0.1-1ms for similar work
- **Realistic speedup**: 10-50x improvement (not millions!)
- **WebAssembly**: Browser-ready with excellent performance

### The Real Innovation: Democratization

Making 60-year-old aerospace algorithms accessible through modern deployment:
- **Open source**: Free alternative to $50K+ commercial licenses
- **Browser deployment**: WebAssembly compilation for web applications
- **Mobile ready**: Runs on phones and tablets  
- **Modern integration**: Easy embedding in AI/ML workflows

## 🛠️ Installation & Usage

### Python Implementation
```bash
# Clone the repository
git clone https://github.com/jhammant/aircraft-datcom.git
cd aircraft-datcom/datcom-python

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

```python
import datcom

# Basic aircraft configuration
aircraft = datcom.Aircraft(
    wingspan=35.0,           # feet
    wing_area=174.0,        # square feet
    wing_sweep=0.0,         # degrees
    tail_volume=0.5,        # horizontal tail volume coefficient
    cg_position=25.0        # percent MAC
)

# Analyze stability and performance
results = datcom.analyze(aircraft, flight_condition)
print(f"Static margin: {results.static_margin}% MAC")
print(f"Neutral point: {results.neutral_point}% MAC") 
print(f"Stall speed: {results.stall_speed} mph")
```

### Rust Implementation
```bash
# Clone the repository
git clone https://github.com/jhammant/aircraft-datcom.git
cd aircraft-datcom/datcom-rs

# Add to your Cargo.toml
# aircraft-datcom-rs = { path = "../aircraft-datcom/datcom-rs" }
```

```rust
use aircraft_datcom_rs::*;

let aircraft = Aircraft::new()
    .wingspan(35.0)
    .wing_area(174.0)
    .wing_sweep(0.0)
    .cg_position(25.0);
    
let results = analyze(&aircraft, &flight_condition);
println!("Analysis completed in: {:?}", results.computation_time);
println!("Static margin: {:.1}% MAC", results.static_margin);
```

### WebAssembly (Browser)
```html
<!DOCTYPE html>
<html>
<head>
    <script type="module">
        // Note: WebAssembly package under development
        // For now, try the live demo at jhammant.github.io/datcom/
        
        // Future usage:
        // import init, { analyze_aircraft } from './pkg/aircraft_datcom.js';
        
        // const results = analyze_aircraft({
        //     wingspan: 35.0,
        //     wing_area: 174.0,
        //     wing_sweep: 0.0,
        //     cg_position: 25.0
        // });
    </script>
</head>
<body>
    <h1>Try the live demo: <a href="https://jhammant.github.io/datcom/">jhammant.github.io/datcom/</a></h1>
</body>
</html>
```

## 🎯 What You Can Build

**Educational Applications:**
- Interactive aerospace engineering textbooks
- Browser-based design exploration tools  
- Mobile apps for students and engineers
- Real-time parameter optimization interfaces

**Preliminary Design Tools:**
- Web-based aircraft configuration analysis
- Quick feasibility studies without expensive software
- Shareable design studies via URLs
- Integration with modern development frameworks

**Research & Development:**
- AI/ML training pipelines with validated physics
- Automated design exploration systems
- Monte Carlo simulation workflows
- Modern aerospace startup applications

## 📁 Project Structure

```
aircraft-datcom/
├── datcom-python/          # Python implementation (in development)
│   ├── datcom/            # Core Python module  
│   ├── tests/             # Validation test suite
│   ├── requirements.txt   # Python dependencies
│   └── examples/          # Usage examples
├── datcom-rs/             # Rust implementation (in development)
│   ├── src/               # Rust source code
│   ├── Cargo.toml         # Rust dependencies
│   ├── benches/           # Performance benchmarks
│   └── tests/             # Rust test suite
├── wasm-pkg/              # WebAssembly bindings (planned)
├── validation/            # Cross-validation against original
├── docs/                  # Documentation
└── examples/              # Complete usage examples
    └── web-demo/          # Live demo source code
```

## 🚧 Development Status

**Current Status:**
- ✅ **Live WebAssembly demo** - Functional in browser
- 🚧 **Python implementation** - Core algorithms in development  
- 🚧 **Rust implementation** - Performance optimization in progress
- 📋 **Package distribution** - PyPI/Crates.io packages planned

**Try Now:**
- **Live Demo**: [jhammant.github.io/datcom/](https://jhammant.github.io/datcom/) - Working WebAssembly interface
- **Source Code**: Available in this repository for development/contribution

## 🏗️ Heritage & Modern Balance

This project preserves the mathematical accuracy of the original algorithms while making them accessible through modern languages and deployment methods. Every calculation will be validated against the original Fortran to ensure aerospace-grade accuracy.

**The goal:** Democratize aerospace analysis. A garage startup should have access to the same algorithms that Boeing uses.

## 🤝 Contributing

Contributions welcome! This is about preserving and modernizing aerospace heritage for everyone.

### Development Setup
```bash
# Clone the repository
git clone https://github.com/jhammant/aircraft-datcom.git
cd aircraft-datcom

# Python development (when ready)
cd datcom-python
pip install -r requirements.txt
pip install -e .
# pytest tests/  # When test suite is complete

# Rust development (when ready)  
cd datcom-rs
# cargo test    # When implementation is complete
# cargo bench   # Performance benchmarks
```

### Contribution Guidelines
- Maintain mathematical accuracy vs original algorithms
- Include comprehensive tests for new features
- Document heritage connections where applicable
- Preserve the historical significance of the codebase

## 📊 Validation & Testing

All implementations will be validated against:
- Original Fortran reference calculations
- Published test cases from USAF documentation  
- Known aircraft configurations (F-16, Cessna 172, etc.)
- Wind tunnel data correlation studies

## 📜 License

**Public Domain** - These algorithms belong to humanity. The original work was developed with public funds for public benefit.

The mathematical foundations of aerospace engineering should be free and accessible to all.

## 🌟 Acknowledgments

- **USAF Wright-Patterson AFB** - Original DATCOM development (1960s-80s)
- **NASA** - Technical documentation and validation data
- **Aerospace community** - Decades of validation and refinement
- **Open source contributors** - Modernization and preservation efforts

## 🔗 Links

- **Live Demo**: [jhammant.github.io/datcom/](https://jhammant.github.io/datcom/) ← **Try it now!**
- **Documentation**: [Full project documentation](docs/) (in development)
- **Heritage Info**: [Historical background](docs/heritage.md) (planned)

---

## 🌙 Vision

**The algorithms that got us to the moon should be free for anyone trying to get us back there.**

As we prepare for Artemis and humanity's return to lunar exploration, the mathematical foundations that enabled Apollo should be accessible to the next generation of aerospace engineers, startups, and dreamers worldwide.

This isn't just code preservation—it's democratizing the tools that design the future of flight.

---

*Heritage algorithms • Modern accessibility • Open source forever*
