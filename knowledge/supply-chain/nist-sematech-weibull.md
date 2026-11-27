# NIST/SEMATECH e-Handbook : 8.1.6.2 Weibull

> Source : NIST/SEMATECH e-Handbook of Statistical Methods, § 8.1.6.2 « Weibull » : https://www.itl.nist.gov/div898/handbook/apr/section1/apr162.htm (consulté le 2026-11-21)
> Licence : publication du NIST, administration fédérale des États-Unis (domaine public, 17 U.S.C. § 105). Texte brut converti, formules LaTeX et scripts retirés ; les courbes (PDF, taux de panne) ne sont pas reprises.
> Note : le texte n'écrit pas « bêta > 1 = usure » ; il donne le taux de panne en puissance (gamma - 1) : constant pour gamma = 1, croissant pour gamma > 1 (déduction à partir de la formule).


8.1.6.2. Weibull
8.
Assessing Product Reliability
8.1.
Introduction
8.1.6.
What are the basic lifetime distribution models used for non-repairable
populations?
8.1.6.2.
Weibull
Weibull Formulas
Formulas and Plots
The Weibull is a very flexible life distribution model with two parameters.
It has CDF and PDF and other key formulas given by:
$$ 
\begin{array}{ll}
\mbox{PDF:}          & f(t, \gamma, \alpha) = \frac{\gamma}{t} \left( \frac{t}{\alpha} \right)^\gamma e^{- \left( \frac{t}{\alpha} \right)^\gamma} \\
                     & \\
\mbox{CDF:}          & F(t) = 1-e^{- \left( \frac{t}{\alpha} \right)^\gamma} \\
                     & \\
\mbox{Reliability:}  & R(t) = e^{- \left( \frac{t}{\alpha} \right)^\gamma} \\
                     & \\
\mbox{Failure Rate:} & h(t) =  \frac{\gamma}{\alpha} \left( \frac{t}{\alpha} \right) ^{\gamma-1} \\
                     & \\
\mbox{Mean:}         & \alpha \Gamma \left(1+\frac{1}{\gamma} \right) \\
                     & \\
\mbox{Median:}       & \alpha (\mbox{ln} \, 2)^{\frac{1}{\gamma}} \\
                     & \\
\mbox{Variance:}     & \alpha^2 \Gamma \left( 1+\frac{2}{\gamma} \right) - \left[ \alpha \Gamma \left( 1 + \frac{1}{\gamma}\right) \right]^2 
\end{array} 
$$
with \(\alpha\)
the scale parameter (the Characteristic Life), \(\gamma\)
(gamma) the Shape Parameter, and \(\Gamma\)
is the Gamma function with \(\Gamma(N) = (N-1)!\)
for integer \(N\).
The cumulative hazard function for the Weibull is the integral of the failure
rate or 
$$ H(t) = \left( \frac{t}{\alpha} \right)^\gamma \,\, . $$
A more general three-parameter form of the Weibull includes an additional
waiting time parameter \(\mu\)
(sometimes called a shift or location parameter). The formulas for the 3-parameter
Weibull are easily obtained from the above formulas by replacing \(t\) by (\(t-\mu)\)
wherever \(t\)
appears. No failure can occur before \(\mu\)
hours,
so the time scale starts at \(\mu\),
and not 0. If a shift parameter \(\mu\)
is known (based, perhaps, on the physics of the failure mode), 
then all you have to do is subtract \(\mu\)
from all the observed failure times and/or readout times and 
analyze the resulting shifted data with a two-parameter Weibull.
NOTE: Various texts and articles in the literature use a variety
of different symbols for the same Weibull parameters. For example, the
characteristic life is sometimes called \(c\) (\(\nu\) = nu or \(\eta\) = eta)
and the shape parameter is also called \(m\) (or \(\beta\) = beta).
To add to the confusion, some software uses \(\beta\)
as the characteristic life parameter and \(\alpha\)
as the shape parameter. Some authors even parameterize the density function 
differently, using a scale parameter \(\theta = \alpha^\gamma\).
Special Case: When \(\gamma\) = 1,
the Weibull reduces to the Exponential Model, 
with \(\alpha = 1/\lambda\)
= the mean time to fail (MTTF).
Depending on the value of the shape parameter \(\gamma\),
the Weibull model can empirically fit a wide range of data histogram
shapes.  This is shown by the PDF example curves below.
Weibull data "shapes"
From a failure rate model viewpoint, the Weibull is a natural
extension of the constant failure rate exponential model since the
Weibull has a polynomial failure rate with exponent {\(\gamma - 1\)}.
This makes all the failure rate curves shown in the following plot
possible.
Weibull failure rate "shapes"
The Weibull is very flexible and also has theoretical
justification in many applications
Uses of the Weibull Distribution Model
Because of its flexible shape and ability to model a wide range of
failure rates, the Weibull has been used successfully in many applications
as a purely empirical model.
The Weibull model can be derived theoretically as a form of 
Extreme Value Distribution, 
governing the time to occurrence of the "weakest link" 
of many competing failure processes. This may explain why it has
been so successful in applications such as capacitor, ball bearing, relay
and material strength failures.
Another special case of the Weibull occurs when the shape parameter
is 2. The distribution is called the Rayleigh Distribution and it turns
out to be the theoretical probability model for the magnitude of radial
error when the \(x\) and \(y\)
coordinate errors are independent normals with 0 mean and the same standard deviation.
Weibull probability plot
We generated 100 Weibull random variables using \(T\) = 1000, 
\(\gamma\) = 1.5 and \(\alpha\) = 5000.
To see how well these random 
Weibull data points are actually fit by a Weibull distribution, 
we generated the probability plot shown below. Note the log scale used is base 10.
If the data follow a Weibull distribution, the points should follow a straight line.
We can comput the PDF and CDF values for failure time \(T\) = 1000, using the 
example Weibull distribution with 
\(\gamma\) = 1.5 and \(\alpha\) = 5000.
The PDF value is 0.000123 and the CDF value is 0.08556.
Functions for computing Weibull PDF values, CDF values, and for producing
probability plots, are found in both Dataplot code 
and R code.
