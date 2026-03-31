from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name='pydatcom',
    version='1.0.0',
    author='USAF/Wright-Patterson AFB (Original), Python Port',
    description='USAF Digital DATCOM in Python - Aircraft stability and control analysis',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/jhammant/aircraft-datcom',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering :: Physics',
    ],
    python_requires='>=3.8',
    install_requires=[
        'numpy>=1.20.0',
        'scipy>=1.7.0',
        'matplotlib>=3.3.0',
    ],
    entry_points={
        'console_scripts': [
            'pydatcom=pydatcom.cli:main',
        ],
    },
)
