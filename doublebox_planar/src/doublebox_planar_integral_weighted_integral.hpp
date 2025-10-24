#ifndef doublebox_planar_integral_weighted_integral_hpp_included
#define doublebox_planar_integral_weighted_integral_hpp_included

#include <vector> // std::vector
#include <string> // std::string

#include "doublebox_planar.hpp"
#include "doublebox_planar_integral/doublebox_planar_integral.hpp"

namespace doublebox_planar
{
    namespace doublebox_planar_integral
    {
        template<typename integrator_t>
        std::vector<nested_series_t<sum_t>> make_integral
        (
            const std::vector<real_t>& real_parameters,
            const std::vector<complex_t>& complex_parameters,
            const integrator_t& integrator
            #if doublebox_planar_contour_deformation
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
