#include "contour_deformation_sector_6_0.hpp"
namespace doublebox_planar_integral
{
#ifdef SECDEC_WITH_CUDA
#define SecDecInternalRealPart(x) (complex_t{x}).real()
#else
#define SecDecInternalRealPart(x) std::real(x)
#endif
integrand_return_t sector_6_order_0_contour_deformation_polynomial
(
    real_t const * restrict const integration_variables,
    real_t const * restrict const real_parameters,
    complex_t const * restrict const complex_parameters,
    real_t const * restrict const deformation_parameters,
    secdecutil::ResultInfo * restrict const result_info
)
{
    const auto x0 = integration_variables[0]; (void)x0;
    const auto x1 = integration_variables[1]; (void)x1;
    const auto x2 = integration_variables[2]; (void)x2;
    const auto x3 = integration_variables[3]; (void)x3;
    const auto x4 = integration_variables[4]; (void)x4;
    const auto x5 = integration_variables[5]; (void)x5;
    const auto s = real_parameters[0]; (void)s;
    const auto t = real_parameters[1]; (void)t;
    const auto msq = real_parameters[2]; (void)msq;
    const auto SecDecInternalLambda0 = deformation_parameters[0]; (void)SecDecInternalLambda0;
    const auto SecDecInternalLambda1 = deformation_parameters[1]; (void)SecDecInternalLambda1;
    const auto SecDecInternalLambda2 = deformation_parameters[2]; (void)SecDecInternalLambda2;
    const auto SecDecInternalLambda3 = deformation_parameters[3]; (void)SecDecInternalLambda3;
    const auto SecDecInternalLambda4 = deformation_parameters[4]; (void)SecDecInternalLambda4;
    const auto SecDecInternalLambda5 = deformation_parameters[5]; (void)SecDecInternalLambda5;
    auto tmp1_1 = x0 + 2;
    auto tmp3_1 = tmp1_1*x0;
    auto tmp3_2 = tmp3_1 + 1;
    auto tmp1_2 = x0 + 1;
    auto tmp1_3 = x4 + 2*tmp1_2;
    auto tmp1_4 = tmp1_3*x4;
    auto tmp3_3 = tmp1_4 + tmp3_2;
    auto tmp1_5 = tmp1_2 + x4;
    auto tmp1_6 = x2 + 3*tmp1_5;
    auto tmp3_4 = tmp1_6*x2;
    auto tmp3_5 = tmp3_4 + tmp3_3;
    auto tmp3_6 = tmp3_5*x1;
    auto tmp1_7 = tmp1_5 + x2;
    auto tmp1_8 = x3 + 1;
    auto tmp1_9 = tmp1_8 + x5;
    auto tmp3_7 = tmp1_7*tmp1_9;
    auto tmp3_8 = tmp3_6 + 2*tmp3_7;
    auto tmp3_9 = tmp3_8*msq;
    auto tmp3_10 = x4*s;
    auto tmp1_10 = s + t;
    auto tmp1_11 = tmp1_10*x0;
    auto tmp1_12 = x2*tmp1_11;
    auto tmp3_11 = -tmp3_10 + tmp1_12;
    auto tmp3_12 = x1*tmp3_11;
    auto tmp3_13 = tmp3_12 + tmp3_9;
    auto tmp1_13 = tmp3_10*x1;
    auto tmp1_14 = x2 + 1;
    auto tmp1_15 = -tmp1_14*tmp1_13;
    auto tmp3_14 = tmp1_2 + x2;
    auto tmp3_15 = -s*tmp3_14;
    auto tmp3_16 = tmp3_9 + tmp1_15-tmp3_10 + tmp3_15;
    auto tmp3_17 = tmp1_5*tmp1_9;
    auto tmp3_18 = 3*tmp3_17;
    auto tmp1_16 = 2*tmp1_5;
    auto tmp1_17 = x2*tmp1_16;
    auto tmp3_19 = tmp1_17 + tmp3_3;
    auto tmp3_20 = x1*tmp3_19;
    auto tmp1_18 = tmp1_9*x2;
    auto tmp3_21 = tmp3_20 + tmp3_18 + 2*tmp1_18;
    auto tmp3_22 = x1*tmp3_21;
    auto tmp3_23 = x5 + 2*tmp1_8;
    auto tmp3_24 = tmp3_23*x5;
    auto tmp1_19 = x3 + 2;
    auto tmp3_25 = tmp1_19*x3;
    auto tmp3_26 = tmp3_24 + tmp3_25 + 1;
    auto tmp3_27 = tmp3_22 + tmp3_26;
    auto tmp3_28 = msq*tmp3_27;
    auto tmp3_29 = x5*tmp1_11;
    auto tmp3_30 = tmp3_10*x3;
    auto tmp3_31 = -s + tmp3_29-tmp3_30;
    auto tmp3_32 = -tmp1_13 + tmp3_31;
    auto tmp3_33 = x1*tmp3_32;
    auto tmp3_34 = x3*s;
    auto tmp3_35 = tmp3_28-tmp3_34 + tmp3_33;
    auto tmp3_36 = tmp1_16 + x2;
    auto tmp3_37 = x1*x2;
    auto tmp3_38 = tmp3_36*tmp3_37;
    auto tmp3_39 = 3*tmp1_18 + tmp3_38 + 2*tmp3_17;
    auto tmp3_40 = tmp3_39*x1;
    auto tmp3_41 = tmp3_40 + tmp3_26;
    auto tmp3_42 = tmp3_41*msq;
    auto tmp3_43 = tmp3_42-tmp3_34;
    auto tmp3_44 = tmp3_37*tmp1_10*x5;
    auto tmp3_45 = tmp3_44 + tmp3_43;
    auto tmp3_46 = -tmp3_34*tmp1_14;
    auto tmp3_47 = x5 + 1;
    auto tmp1_20 = -tmp3_37-tmp3_47;
    auto tmp3_48 = s*tmp1_20;
    auto tmp3_49 = tmp3_48 + tmp3_46;
    auto tmp3_50 = x1*tmp3_49;
    auto tmp3_51 = tmp3_50 + tmp3_43;
    auto tmp3_52 = tmp1_9*tmp3_2;
    auto tmp3_53 = x4*tmp1_9*tmp1_3;
    auto tmp3_54 = tmp3_18 + tmp1_18;
    auto tmp3_55 = x2*tmp3_54;
    auto tmp3_56 = x2*tmp1_5;
    auto tmp3_57 = tmp3_56 + tmp3_3;
    auto tmp3_58 = 2*tmp3_37;
    auto tmp3_59 = tmp3_57*tmp3_58;
    auto tmp3_60 = tmp3_59 + tmp3_55 + tmp3_53 + tmp3_52;
    auto tmp3_61 = msq*tmp3_60;
    auto tmp3_62 = -s*tmp3_47;
    auto tmp3_63 = -tmp3_34 + tmp3_62;
    auto tmp3_64 = x4*tmp3_63;
    auto tmp3_65 = x2*tmp3_31;
    auto tmp3_66 = -tmp3_10*tmp3_58;
    auto tmp3_67 = tmp3_61 + tmp3_66 + tmp3_64 + tmp3_65;
    auto tmp3_68 = 2*msq;
    auto tmp3_69 = tmp3_68-s;
    auto tmp3_70 = 3*msq;
    auto tmp3_71 = tmp3_70-s;
    auto tmp3_72 = tmp3_70 + tmp1_10;
    auto tmp3_73 = -1 + x5;
    auto tmp3_74 = x5*SecDecInternalLambda5*tmp3_73;
    auto tmp3_75 = -1 + x3;
    auto tmp3_76 = x3*SecDecInternalLambda3*tmp3_75;
    auto tmp3_77 = -1 + x2;
    auto tmp3_78 = x2*SecDecInternalLambda2*tmp3_77;
    auto tmp3_79 = -1 + x0;
    auto tmp3_80 = x0*SecDecInternalLambda0*tmp3_79;
    auto tmp3_81 = -1 + x4;
    auto tmp3_82 = x4*SecDecInternalLambda4*tmp3_81;
    auto tmp3_83 = -1 + x1;
    auto tmp3_84 = x1*SecDecInternalLambda1*tmp3_83;
    auto __RealPartCall1 = SecDecInternalRealPart(tmp3_67);
    auto __RealPartCall2 = SecDecInternalRealPart(tmp3_51);
    auto __RealPartCall3 = SecDecInternalRealPart(tmp3_45);
    auto __RealPartCall4 = SecDecInternalRealPart(tmp3_35);
    auto __RealPartCall5 = SecDecInternalRealPart(tmp3_16);
    auto __RealPartCall6 = SecDecInternalRealPart(tmp3_13);
    auto __Deformedx0Call = x0 + i_*__RealPartCall3*tmp3_80;
    auto __Deformedx1Call = x1 + i_*__RealPartCall1*tmp3_84;
    auto __Deformedx2Call = x2 + i_*__RealPartCall4*tmp3_78;
    auto __Deformedx3Call = x3 + i_*__RealPartCall5*tmp3_76;
    auto __Deformedx4Call = x4 + i_*__RealPartCall2*tmp3_82;
    auto __Deformedx5Call = x5 + i_*__RealPartCall6*tmp3_74;
    return(__Deformedx5Call*tmp3_68 + __Deformedx4Call*__Deformedx5Call*tmp3_68 + __Deformedx3Call*tmp3_69 + __Deformedx3Call*__Deformedx5Call*tmp3_68 + __Deformedx3Call*__Deformedx4Call*tmp3_69 + __Deformedx3Call*__Deformedx4Call*__Deformedx5Call*tmp3_68 + __Deformedx2Call*__Deformedx5Call*tmp3_68 + __Deformedx2Call*__Deformedx3Call*tmp3_69 + __Deformedx2Call*__Deformedx3Call*__Deformedx5Call*tmp3_68 + __Deformedx1Call*__Deformedx4Call*tmp3_69 + __Deformedx1Call*__Deformedx4Call*__Deformedx5Call*tmp3_69 + __Deformedx1Call*__Deformedx3Call*__Deformedx4Call*tmp3_69 + __Deformedx1Call*__Deformedx2Call*tmp3_71 + __Deformedx1Call*__Deformedx2Call*__Deformedx5Call*tmp3_70 + __Deformedx1Call*__Deformedx2Call*__Deformedx4Call*tmp3_70 + __Deformedx1Call*__Deformedx2Call*__Deformedx4Call*__Deformedx5Call*tmp3_70 + __Deformedx1Call*__Deformedx2Call*__Deformedx3Call*tmp3_70 + __Deformedx1Call*__Deformedx2Call*__Deformedx3Call*__Deformedx4Call*tmp3_71 + SecDecInternalSqr(__Deformedx1Call)*__Deformedx2Call*__Deformedx4Call*tmp3_69 + __Deformedx0Call*__Deformedx5Call*tmp3_68 + __Deformedx0Call*__Deformedx3Call*tmp3_69 + __Deformedx0Call*__Deformedx3Call*__Deformedx5Call*tmp3_68 + __Deformedx0Call*__Deformedx1Call*tmp3_68 + __Deformedx0Call*__Deformedx1Call*__Deformedx5Call*tmp3_68 + __Deformedx0Call*__Deformedx1Call*__Deformedx4Call*tmp3_68 + __Deformedx0Call*__Deformedx1Call*__Deformedx4Call*__Deformedx5Call*tmp3_68 + __Deformedx0Call*__Deformedx1Call*__Deformedx3Call*tmp3_68 + __Deformedx0Call*__Deformedx1Call*__Deformedx3Call*__Deformedx4Call*tmp3_68 + __Deformedx0Call*__Deformedx1Call*__Deformedx2Call*tmp3_70 + __Deformedx0Call*__Deformedx1Call*__Deformedx2Call*__Deformedx5Call*tmp3_72 + __Deformedx0Call*__Deformedx1Call*__Deformedx2Call*__Deformedx3Call*tmp3_70 + __Deformedx0Call*SecDecInternalSqr(__Deformedx1Call)*__Deformedx2Call*tmp3_68 + __Deformedx0Call*SecDecInternalSqr(__Deformedx1Call)*__Deformedx2Call*__Deformedx4Call*tmp3_68 + msq + msq*SecDecInternalSqr(__Deformedx5Call)+msq*__Deformedx4Call + msq*__Deformedx4Call*SecDecInternalSqr(__Deformedx5Call)+msq*SecDecInternalSqr(__Deformedx3Call)+msq*SecDecInternalSqr(__Deformedx3Call)*__Deformedx4Call + msq*__Deformedx2Call + msq*__Deformedx2Call*SecDecInternalSqr(__Deformedx5Call)+msq*__Deformedx2Call*SecDecInternalSqr(__Deformedx3Call)+msq*__Deformedx1Call + msq*__Deformedx1Call*__Deformedx5Call + msq*__Deformedx1Call*SecDecInternalSqr(__Deformedx4Call)+msq*__Deformedx1Call*SecDecInternalSqr(__Deformedx4Call)*__Deformedx5Call + msq*__Deformedx1Call*__Deformedx3Call + msq*__Deformedx1Call*__Deformedx3Call*SecDecInternalSqr(__Deformedx4Call)+msq*__Deformedx1Call*SecDecInternalSqr(__Deformedx2Call)+msq*__Deformedx1Call*SecDecInternalSqr(__Deformedx2Call)*__Deformedx5Call + msq*__Deformedx1Call*SecDecInternalSqr(__Deformedx2Call)*__Deformedx3Call + msq*SecDecInternalSqr(__Deformedx1Call)*__Deformedx2Call + msq*SecDecInternalSqr(__Deformedx1Call)*__Deformedx2Call*SecDecInternalSqr(__Deformedx4Call)+msq*SecDecInternalSqr(__Deformedx1Call)*SecDecInternalSqr(__Deformedx2Call)+msq*SecDecInternalSqr(__Deformedx1Call)*SecDecInternalSqr(__Deformedx2Call)*__Deformedx4Call + msq*__Deformedx0Call + msq*__Deformedx0Call*SecDecInternalSqr(__Deformedx5Call)+msq*__Deformedx0Call*SecDecInternalSqr(__Deformedx3Call)+msq*__Deformedx0Call*SecDecInternalSqr(__Deformedx1Call)*SecDecInternalSqr(__Deformedx2Call)+msq*SecDecInternalSqr(__Deformedx0Call)*__Deformedx1Call + msq*SecDecInternalSqr(__Deformedx0Call)*__Deformedx1Call*__Deformedx5Call + msq*SecDecInternalSqr(__Deformedx0Call)*__Deformedx1Call*__Deformedx3Call + msq*SecDecInternalSqr(__Deformedx0Call)*SecDecInternalSqr(__Deformedx1Call)*__Deformedx2Call);
}
}
