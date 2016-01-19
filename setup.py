from setuptools import setup

import edi

setup(name='Edi',
      description='Simple and elegant Slack bot',
      version=edi.__version__,
      author='John Reese',
      author_email='john@noswap.com',
      url='https://github.com/jreese/edi',
      classifiers=['License :: OSI Approved :: MIT License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.4',
                   'Programming Language :: Python :: 3.5',
                   'Topic :: Utilities',
                   'Development Status :: 4 - Beta',
                   ],
      license='MIT License',
      packages=['edi'],
      package_data={'edi': ['defaults.yaml']},
      install_requires=['ent', 'slacker'],
      scripts=['bin/edi'],
      )
