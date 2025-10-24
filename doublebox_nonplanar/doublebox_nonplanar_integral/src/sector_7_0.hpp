#ifndef doublebox_nonplanar_integral_codegen_sector_7_0_hpp_included
#define doublebox_nonplanar_integral_codegen_sector_7_0_hpp_included
#include "doublebox_nonplanar_integral.hpp"
#include "functions.hpp"
#include "contour_deformation_sector_7_0.hpp"
namespace doublebox_nonplanar_integral
{
#ifdef SECDEC_WITH_CUDA
__host__ __device__
#endif
secdecutil::SectorContainerWithDeformation<real_t, complex_t>::DeformedIntegrandFunction sector_7_order_0_integrand;
#ifdef SECDEC_WITH_CUDA
secdecutil::SectorContainerWithDeformation<real_t, complex_t>::DeformedIntegrandFunction* get_device_sector_7_order_0_integrand();
#endif
}
#endif
