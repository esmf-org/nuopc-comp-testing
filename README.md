# nuopc-comp-testing

This action allows testing model components in a isolated enviroment outside of any Earth system modeling application. In this case, the model component can be forced by data components that are provided by the Community Data Models for Earth Prediction Systems ([CDEPS](https://github.com/ESCOMP/CDEPS)). 

The action mainly includes following features;

- Installs component dependencies such as third-party libraries required to build model component through the use of [Spack package manager](https://github.com/spack/spack)

- Creates very simple executable that includes the active component and data model through the use of Earth System Model eXecutable layer ([ESMX](https://github.com/esmf-org/esmf/tree/develop/src/addon/ESMX)).

- Prepares run directory for testing specified configuration.
  - a
