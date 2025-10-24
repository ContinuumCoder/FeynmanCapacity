#ifndef doublebox_planar_integral_codegen_sector_15_0_hpp_included
#define doublebox_planar_integral_codegen_sector_15_0_hpp_included
#include "doublebox_planar_integral.hpp"
#include "functions.hpp"
#include "contour_deformation_sector_15_0.hpp"
namespace doublebox_planar_integral
{
#ifdef SECDEC_WITH_CUDA
__host__ __device__
#endif
secdecutil::SectorContainerWithDeformation<real_t, complex_t>::DeformedIntegrandFunction sector_15_order_0_integrand;
#ifdef SECDEC_WITH_CUDA
secdecutil::SectorContainerWithDeformation<real_t, complex_t>::DeformedIntegrandFunction* get_device_sector_15_order_0_integrand();
#endif
}
#endif
