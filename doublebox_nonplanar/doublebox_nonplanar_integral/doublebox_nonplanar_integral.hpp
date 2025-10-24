#ifndef doublebox_nonplanar_integral_hpp_included
#define doublebox_nonplanar_integral_hpp_included

#ifdef SECDEC_WITH_CUDA
    #include <thrust/complex.h>
#else
    #include <complex>
#endif
#include <string>
#include <vector>
#include <secdecutil/integrand_container.hpp>
#include <secdecutil/sector_container.hpp>
#include <secdecutil/series.hpp>
#include <secdecutil/uncertainties.hpp>

namespace doublebox_nonplanar_integral
{
    // whether or not to use contour deformation
    #define doublebox_nonplanar_integral_contour_deformation 1

    // whether or not complex parameters are present
    #define doublebox_nonplanar_integral_has_complex_parameters 0

    // whether or not the return type should be complex in any case
    #define doublebox_nonplanar_integral_enforce_complex_return_type 0

    // basic data types
    // --{
    typedef double real_t;
    #ifdef SECDEC_WITH_CUDA
        typedef thrust::complex<real_t> complex_t;
    #else
        typedef std::complex<real_t> complex_t;
    #endif
    #if doublebox_nonplanar_integral_has_complex_parameters || doublebox_nonplanar_integral_contour_deformation || doublebox_nonplanar_integral_enforce_complex_return_type
        typedef complex_t integrand_return_t;
    #else
        typedef real_t integrand_return_t;
    #endif
    #if doublebox_nonplanar_integral_contour_deformation
        typedef secdecutil::SectorContainerWithDeformation<real_t,complex_t> sector_container_t;
    #else
        typedef secdecutil::SectorContainerWithoutDeformation<real_t,complex_t,integrand_return_t> sector_container_t;
    #endif
    template<typename T> using nested_series_t = secdecutil::Series<T>;
    typedef secdecutil::IntegrandContainer<integrand_return_t, real_t const * const, real_t> integrand_t;
    // --}

    const std::string package_name = "doublebox_nonplanar_integral";

    const unsigned long long number_of_sectors = 18;

    const unsigned int maximal_number_of_integration_variables = 6;

    const unsigned int number_of_regulators = 1;
    const std::vector<std::string> names_of_regulators = {"eps"};

    const unsigned int number_of_real_parameters = 3;
    const std::vector<std::string> names_of_real_parameters = {"s","t","msq"};

    const unsigned int number_of_complex_parameters = 0;
    const std::vector<std::string> names_of_complex_parameters = {};

    const std::vector<int> lowest_orders = {0}; // not including the prefactor
    const std::vector<int> highest_orders = {0}; // not including the prefactor
    const std::vector<int> lowest_prefactor_orders = {0};
    const std::vector<int> highest_prefactor_orders = {0};
    const std::vector<int> requested_orders = {0};

    const std::vector<nested_series_t<sector_container_t>>& get_sectors();
    nested_series_t<integrand_return_t> prefactor(const std::vector<real_t>& real_parameters, const std::vector<complex_t>& complex_parameters);

    extern const std::vector<std::vector<real_t>> pole_structures;

    std::vector<nested_series_t<integrand_t>> make_integrands
    (
        const std::vector<real_t>& real_parameters,
        const std::vector<complex_t>& complex_parameters
        #if doublebox_nonplanar_integral_contour_deformation
            ,unsigned number_of_presamples = 100000,
            real_t deformation_parameters_maximum = 1.,
            real_t deformation_parameters_minimum = 1.e-5,
            real_t deformation_parameters_decrease_factor = 0.9
        #endif
    );

    #ifdef SECDEC_WITH_CUDA
        #if doublebox_nonplanar_integral_contour_deformation
            typedef secdecutil::CudaIntegrandContainerWithDeformation
                    <
                        real_t,complex_t,1/*maximal_number_of_functions*/,
                        maximal_number_of_integration_variables,
                        number_of_real_parameters,number_of_complex_parameters,
                        'd','o','u','b','l','e','b','o','x','_','n','o','n','p','l','a','n','a','r','_','i','n','t','e','g','r','a','l'
                    >
                    cuda_integrand_t;
            typedef secdecutil::CudaIntegrandContainerWithDeformation
                    <
                        real_t,complex_t,number_of_sectors/*maximal_number_of_functions*/,
                        maximal_number_of_integration_variables,
                        number_of_real_parameters,number_of_complex_parameters,
                        'd','o','u','b','l','e','b','o','x','_','n','o','n','p','l','a','n','a','r','_','i','n','t','e','g','r','a','l'
                    >
                    cuda_together_integrand_t;
            std::vector<nested_series_t<cuda_integrand_t>> make_cuda_integrands
            (
                const std::vector<real_t>& real_parameters,
                const std::vector<complex_t>& complex_parameters,
                unsigned number_of_presamples = 100000,
                real_t deformation_parameters_maximum = 1.,
                real_t deformation_parameters_minimum = 1.e-5,
                real_t deformation_parameters_decrease_factor = 0.9
            );
        #else
            typedef secdecutil::CudaIntegrandContainerWithoutDeformation
                    <
                        real_t,complex_t,integrand_return_t,
                        1/*maximal_number_of_functions*/,
                        number_of_real_parameters,number_of_complex_parameters,
                        'd','o','u','b','l','e','b','o','x','_','n','o','n','p','l','a','n','a','r','_','i','n','t','e','g','r','a','l'
                    >
                    cuda_integrand_t;
            typedef secdecutil::CudaIntegrandContainerWithoutDeformation
                    <
                        real_t,complex_t,integrand_return_t,
                        number_of_sectors/*maximal_number_of_functions*/,
                        number_of_real_parameters,number_of_complex_parameters,
                        'd','o','u','b','l','e','b','o','x','_','n','o','n','p','l','a','n','a','r','_','i','n','t','e','g','r','a','l'
                    >
                    cuda_together_integrand_t;
            std::vector<nested_series_t<cuda_integrand_t>> make_cuda_integrands
            (
                const std::vector<real_t>& real_parameters,
                const std::vector<complex_t>& complex_parameters
            );
        #endif
    #endif

    // Do not undefine integral specific variables
    //#undef doublebox_nonplanar_integral_contour_deformation
    //#undef doublebox_nonplanar_integral_has_complex_parameters
    //#undef doublebox_nonplanar_integral_enforce_complex_return_type

};

#ifdef SECDEC_WITH_CUDA
// provide custom common_type (together + integral) = together
namespace std 
{
    template <>
    struct common_type<doublebox_nonplanar_integral::cuda_together_integrand_t, doublebox_nonplanar_integral::cuda_integrand_t> 
    {
        using type = doublebox_nonplanar_integral::cuda_together_integrand_t;
    };
}
#endif

#endif
