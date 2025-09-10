"""Setup script for leisai package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
here = Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='leisai-l7-driver',
    version='1.0.0',
    author='Leisai Python Driver Team',
    author_email='support@leisai.com',
    description='Python driver for Leisai L7 series servo controllers',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/leisai/python-l7-driver',
    project_urls={
        'Bug Tracker': 'https://github.com/leisai/python-l7-driver/issues',
        'Documentation': 'https://leisai-l7-driver.readthedocs.io',
        'Source Code': 'https://github.com/leisai/python-l7-driver',
    },
    
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Manufacturing',
        'Intended Audience :: Science/Research',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
    ],
    
    keywords='servo, motor, control, modbus, automation, robotics, leisai, l7',
    
    packages=find_packages(exclude=['tests', 'tests.*', 'examples', 'examples.*', 'docs', 'docs.*']),
    
    python_requires='>=3.7',
    
    install_requires=[
        'pyserial>=3.5',
    ],
    
    extras_require={
        'dev': [
            'pytest>=7.0',
            'pytest-cov>=4.0',
            'pytest-asyncio>=0.21',
            'black>=23.0',
            'flake8>=6.0',
            'mypy>=1.0',
            'sphinx>=6.0',
            'sphinx-rtd-theme>=1.2',
        ],
        'test': [
            'pytest>=7.0',
            'pytest-cov>=4.0',
            'pytest-asyncio>=0.21',
            'pytest-mock>=3.10',
        ],
    },
    
    entry_points={
        'console_scripts': [
            'leisai-monitor=leisai.tools.monitor:main',
            'leisai-config=leisai.tools.config:main',
        ],
    },
    
    package_data={
        'leisai': [
            'py.typed',  # PEP 561 type hints marker
        ],
    },
    
    zip_safe=False,
)