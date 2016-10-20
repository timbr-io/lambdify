from setuptools import setup
from setuptools.command.develop import develop as _develop
from notebook.nbextensions import install_nbextension
from notebook.services.config import ConfigManager
import os

extension_dir = os.path.join(os.path.dirname(__file__), "lambdify", "static")

class develop(_develop):
    def run(self):
        _develop.run(self)
        install_nbextension(extension_dir, symlink=True,
                            overwrite=True, user=False, destination="lambdify")
        cm = ConfigManager()
        cm.update('notebook', {"load_extensions": {"lambdify/index": True } })

setup(name='lambdify',
      cmdclass={'develop': develop},
      version='0.0.1',
      description='creates lambda methods from custom code and api gateways to expose them',
      url='https://github.com',
      author='Chris Helm',
      author_email='chelm@timbr.io',
      license='MIT',
      packages=['lambdify'],
      zip_safe=False,
      data_files=[
        ('share/jupyter/nbextensions/lamdify', [
            'lambdify/static/index.js'
        ]),
      ],
      install_requires=[
          'ipython',
          'jupyter-react'
        ]
      )
