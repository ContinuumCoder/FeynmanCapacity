#include <secdecutil/series.hpp>

#include "sector_7_0.hpp"
#include "contour_deformation_sector_7_0.hpp"
#include "optimize_deformation_parameters_sector_7_0.hpp"

namespace doublebox_nonplanar_integral
{
nested_series_t<sector_container_t> get_integrand_of_sector_7()
{
return {0,0,{{7,{0},6,sector_7_order_0_integrand,
#ifdef SECDEC_WITH_CUDA
get_device_sector_7_order_0_integrand,
#endif
sector_7_order_0_contour_deformation_polynomial,sector_7_order_0_maximal_allowed_deformation_parameters}},true,"eps"};
}

}
