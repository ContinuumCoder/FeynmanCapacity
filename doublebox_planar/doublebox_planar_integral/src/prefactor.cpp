#include <secdecutil/series.hpp>
#include <secdecutil/uncertainties.hpp>
#include <vector>

#include "doublebox_planar_integral.hpp"
#include "functions.hpp"

namespace doublebox_planar_integral
{
    nested_series_t<integrand_return_t> prefactor(const std::vector<real_t>& real_parameters, const std::vector<complex_t>& complex_parameters)
    {
        #define s real_parameters.at(0)
        #define t real_parameters.at(1)
        #define msq real_parameters.at(2)
        return {0,0,{{-2.0}},true,"eps"};
        #undef s
        #undef t
        #undef msq
    }
};
