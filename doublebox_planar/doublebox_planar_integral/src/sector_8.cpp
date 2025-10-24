#include <secdecutil/series.hpp>

#include "sector_8_0.hpp"
#include "contour_deformation_sector_8_0.hpp"
#include "optimize_deformation_parameters_sector_8_0.hpp"

namespace doublebox_planar_integral
{
nested_series_t<sector_container_t> get_integrand_of_sector_8()
{
return {0,0,{{8,{0},6,sector_8_order_0_integrand,
#ifdef SECDEC_WITH_CUDA
get_device_sector_8_order_0_integrand,
#endif
sector_8_order_0_contour_deformation_polynomial,sector_8_order_0_maximal_allowed_deformation_parameters}},true,"eps"};
}

}
