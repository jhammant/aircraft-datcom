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
- **Planned Python implementation**: ~1-10ms for typical aerodynamic calculations
- **Planned Rust implementation**: ~0.1-1ms for similar work
- **Target speedup**: 10-50x improvement over current Python wrappers
- **WebAssembly demo**: Already functional in browser with excellent performance

### The Real Innovation: Democratization

Making 60-year-old aerospace algorithms accessible through modern deployment:
- **Open source**: Free alternative to $50K+ commercial licenses
- **Browser deployment**: WebAssembly compilation for web applications
- **Mobile ready**: Runs on phones and tablets  
- **Modern integration**: Easy embedding in AI/ML workflows

## 🛠️ Current Status & Usage

### ✅ What's Working Right Now
**Live WebAssembly Demo**: [https://jhammant.github.io/datcom/](https://jhammant.github.io/datcom/)
- Real-time aircraft configuration analysis
- Interactive parameter adjustment
- Professional aerospace interface
- Mobile-responsive design

### 🚧 What's In Development

#### Python Implementation
```bash
# Clone the repository
git clone https://github.com/jhammant/aircraft-datcom.git
cd aircraft-datcom

# Python implementation is currently being developed
# The core algorithms are being ported from the original Fortran
# Check back for updates or contribute to development!
```

#### Rust Implementation  
```bash
# Clone the repository
git clone https://github.com/jhammant/aircraft-datcom.git
cd aircraft-datcom

# Rust implementation is planned for maximum performance
# Will target sub-millisecond analysis times
# Contributions welcome for Rust developers!
```

#### Package Distribution
```bash
# Planned future releases:
# pip install aircraft-datcom        # Python package (not yet available)
# cargo add aircraft-datcom-rs       # Rust crate (not yet available)

# For now, clone the repository and try the live demo!
```

## 🎯 What You Can Build (With The Live Demo)

**Educational Applications:**
- Interactive aerospace learning interfaces
- Real-time design exploration tools
- Mobile-friendly analysis applications

**Integration Projects:**
- Embed the demo in educational websites
- Use as reference for algorithm validation
- Prototype aerospace analysis workflows

**Research Applications:**
- Validate preliminary aircraft designs
- Explore parameter sensitivity
- Educational demonstrations

## 🏗️ Contributing to Development

This project needs developers to help port the heritage Fortran algorithms:

### Python Developers Needed
- Port core DATCOM algorithms from Fortran to Python
- Implement validation test suites
- Optimize performance while maintaining accuracy

### Rust Developers Needed  
- Create high-performance Rust implementation
- Target sub-millisecond analysis times
- Implement WebAssembly bindings

### Aerospace Engineers Needed
- Validate algorithms against known aircraft
- Create comprehensive test cases
- Document algorithm heritage and significance

## 📁 Repository Structure

```
aircraft-datcom/
├── docs/                   # Documentation and heritage info
├── original-fortran/       # Original USAF Fortran source (reference)
├── validation/            # Test cases and validation data
├── web-demo/              # Live demo source code (WebAssembly)
├── python-impl/           # Python implementation (in development)
├── rust-impl/             # Rust implementation (planned)
└── examples/              # Usage examples and tutorials
```

## 📊 Development Roadmap

**Phase 1: Foundation** ✅
- ✅ Heritage code analysis and documentation
- ✅ WebAssembly demonstration interface
- ✅ Project structure and contribution guidelines

**Phase 2: Core Implementation** 🚧
- 🚧 Python algorithm porting (in progress)
- 📋 Rust performance implementation (planned)
- 📋 Comprehensive validation test suite

**Phase 3: Distribution** 📋
- 📋 PyPI package publication
- 📋 Crates.io package publication  
- 📋 npm WebAssembly package
- 📋 Documentation website

## 📜 License

**Public Domain** - These algorithms belong to humanity. The original work was developed with public funds for public benefit.

## 🌟 Acknowledgments

- **USAF Wright-Patterson AFB** - Original DATCOM development (1960s-80s)
- **NASA** - Technical documentation and validation data
- **Aerospace community** - Decades of validation and refinement

## 🔗 Links

- **🚀 Live Demo**: [jhammant.github.io/datcom/](https://jhammant.github.io/datcom/) ← **Try it now!**
- **📚 Contribute**: Help port heritage algorithms to modern languages
- **🏛️ Heritage**: Preserve aerospace computing history

---

## 🌙 Vision

**The algorithms that got us to the moon should be free for anyone trying to get us back there.**

As we prepare for Artemis and humanity's return to lunar exploration, the mathematical foundations that enabled Apollo should be accessible to the next generation of aerospace engineers, startups, and dreamers worldwide.

This isn't just code preservation—it's democratizing the tools that design the future of flight.

---

*Heritage algorithms • Modern accessibility • Open source forever*
