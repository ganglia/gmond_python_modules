from distutils.core import setup
from sys import version

# earlier versions don't support all classifiers
if version < '2.2.3':
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None

_package_name='nvidia-ml-py'

setup(name=_package_name,
      version='7.352.0',
      description='Python Bindings for the NVIDIA Management Library',
      py_modules=['pynvml', 'nvidia_smi'],
      package_data={_package_name: ['Example.txt']},
      license="BSD",
      url="http://www.nvidia.com/",
      author="NVIDIA Corporation",
      author_email="nvml-bindings@nvidia.com",
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Hardware',
          'Topic :: System :: Systems Administration',
          ],
      )

