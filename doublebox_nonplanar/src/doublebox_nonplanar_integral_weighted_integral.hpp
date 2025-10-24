#ifndef doublebox_nonplanar_integral_weighted_integral_hpp_included
#define doublebox_nonplanar_integral_weighted_integral_hpp_included

#include <vector> // std::vector
#include <string> // std::string

#include "doublebox_nonplanar.hpp"
#include "doublebox_nonplanar_integral/doublebox_nonplanar_integral.hpp"

namespace doublebox_nonplanar
{
    namespace doublebox_nonplanar_integral
    {
        template<typename integrator_t>
        std::vector<nested_series_t<sum_t>> make_integral
        (
            const std::vector<real_t>& real_parameters,
            const std::vector<complex_t>& complex_parameters,
            const integrator_t& integrator
            #if doublebox_nonplanar_contour_deformation
                ,unsigned number_of_presamples,
                real_t deformation_parameters_maximum,
                real_t deformation_parameters_minimum,
                real_t deformation_parameters_decrease_factor
            #endif
        );
        nested_series_t<sum_t> make_weighted_integral
        (
            const std::vector<real_t>& real_parameters,
            const std::vector<complex_t>& complex_parameters,
            const std::vector<nested_series_t<sum_t>>& integrals,
            const unsigned int amp_idx,
            const std::string& lib_path
        );
    }
};
#endif
