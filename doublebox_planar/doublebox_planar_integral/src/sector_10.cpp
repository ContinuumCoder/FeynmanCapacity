#include <secdecutil/series.hpp>

#include "sector_10_0.hpp"
#include "contour_deformation_sector_10_0.hpp"
#include "optimize_deformation_parameters_sector_10_0.hpp"

namespace doublebox_planar_integral
{
nested_series_t<sector_container_t> get_integrand_of_sector_10()
{
return {0,0,{{10,{0},6,sector_10_order_0_integrand,
#ifdef SECDEC_WITH_CUDA
get_device_sector_10_order_0_integrand,
#endif
sector_10_order_0_contour_deformation_polynomial,sector_10_order_0_maximal_allowed_deformation_parameters}},true,"eps"};
}

}
