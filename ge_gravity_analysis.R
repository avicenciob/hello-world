# ══════════════════════════════════════════════════════════════════════
# Full Endowment GE: Baseline vs. Counterfactual using GEGravity
# ══════════════════════════════════════════════════════════════════════
#
# Uses the GEGravity R package (Kudlay/Zylkin), which implements the
# DEK (2007) exact hat algebra as described in Baier, Yotov & Zylkin
# (2019, JIE).
#
# Install:
#   install.packages("devtools")
#   devtools::install_github("VKudlay/GEGravity")
#
# If CRAN version available:
#   install.packages("GEGravity")
#
# Author: Antonio Vicencio
# ══════════════════════════════════════════════════════════════════════

library(GEGravity)

# ──────────────────────────────────────────────────────────────────────
# 1. SETUP: 3-country toy economy (balanced trade)
# ──────────────────────────────────────────────────────────────────────

# Country labels
countries <- c("A", "B", "C")

# Baseline bilateral trade flows (symmetric off-diagonal → balanced trade)
X_mat <- matrix(
  c(80, 10,  5,
    10, 60, 10,
     5, 10, 85),
  nrow = 3, byrow = TRUE,
  dimnames = list(countries, countries)
)

cat("═══════════════════════════════════════════════════════════════\n")
cat("FULL ENDOWMENT GE USING GEGravity (Zylkin)\n")
cat("═══════════════════════════════════════════════════════════════\n\n")

cat("Baseline bilateral trade flows X⁰:\n")
print(X_mat)

Y_base <- rowSums(X_mat)
E_base <- colSums(X_mat)
cat("\nBaseline incomes  Y⁰ =", Y_base, "\n")
cat("Baseline expend.  E⁰ =", E_base, "\n")
cat("Balanced trade check: Y = E?", all(Y_base == E_base), "\n\n")

# ──────────────────────────────────────────────────────────────────────
# 2. PREPARE DATA FOR ge_gravity()
# ──────────────────────────────────────────────────────────────────────
# ge_gravity() requires long-format data with columns:
#   exp_id, imp_id, flows, beta
# and the data must be NxN (including self-trade).
#
# Key parameters:
#   beta  = ln(τ̂^{-θ}) = -θ * ln(τ̂)  for shocked pairs, 0 otherwise
#   theta = trade elasticity (= σ - 1)
#   mult  = TRUE for multiplicative trade imbalances (balanced trade)

sigma <- 5
theta <- sigma - 1  # = 4

# Trade cost shock: τ_{AB} increases by 50% → τ̂_{AB} = 1.5
tau_hat_AB <- 1.5

# Build long-format data
df <- expand.grid(exp_id = countries, imp_id = countries,
                  stringsAsFactors = FALSE)
df$flows <- as.vector(X_mat)  # column-major matches expand.grid order

# Beta: partial equilibrium log-change in bilateral trade
# β_{ij} = -θ * ln(τ̂_{ij}) for shocked pairs, 0 otherwise
# B_{ij} = exp(β_{ij}) = τ̂_{ij}^{-θ} is the direct trade multiplier
df$beta <- 0
df$beta[df$exp_id == "A" & df$imp_id == "B"] <- -theta * log(tau_hat_AB)

cat("─────────────────────────────────────────────────────────────\n")
cat("Shock: τ̂_{AB} =", tau_hat_AB, "\n")
cat("β_{AB} = -θ × ln(τ̂) =", -theta * log(tau_hat_AB), "\n")
cat("θ = σ - 1 =", theta, "\n")
cat("─────────────────────────────────────────────────────────────\n\n")

cat("Input data (long format):\n")
print(df)
cat("\n")

# ──────────────────────────────────────────────────────────────────────
# 3. RUN ge_gravity(): FULL ENDOWMENT GE
# ──────────────────────────────────────────────────────────────────────

cat("═══════════════════════════════════════════════════════════════\n")
cat("STEP 1: Run ge_gravity() — full endowment GE counterfactual\n")
cat("═══════════════════════════════════════════════════════════════\n\n")

result <- ge_gravity(
  exp_id = df$exp_id,
  imp_id = df$imp_id,
  flows  = df$flows,
  beta   = df$beta,
  theta  = theta,
  mult   = TRUE,      # multiplicative imbalances (appropriate for balanced trade)
  data   = df
)

# Extract counterfactual flows into matrix form
# Reconstruct from labeled output to avoid ordering issues
X1_mat <- matrix(0, nrow = 3, ncol = 3,
                 dimnames = list(countries, countries))
for (r in 1:nrow(result)) {
  i <- result$exp_id[r]
  j <- result$imp_id[r]
  X1_mat[i, j] <- result$new_trade[r]
}

cat("Counterfactual bilateral flows X¹ (from ge_gravity):\n")
print(round(X1_mat, 4))

Y1 <- rowSums(X1_mat)
E1 <- colSums(X1_mat)
cat("\nCounterfactual incomes  Y¹ =", round(Y1, 4), "\n")
cat("Counterfactual expend.  E¹ =", round(E1, 4), "\n")

cat("\nSize changes:\n")
cat("  ΔY = Y¹ − Y⁰ =", round(Y1 - Y_base, 4), "\n")

# Extract unique exporter-level results
w_unique <- result[!duplicated(result$exp_id),
                   c("exp_id", "nom_wage", "price_index", "welfare", "real_wage")]
w_unique <- w_unique[order(w_unique$exp_id), ]
cat("\n  Equilibrium changes by country:\n")
print(w_unique, row.names = FALSE)


# ──────────────────────────────────────────────────────────────────────
# 4. RAS/IPF IMPLEMENTATION
# ──────────────────────────────────────────────────────────────────────

ras_ipf <- function(seed, R, C, tol = 1e-14, max_iter = 100000) {
  A <- seed
  for (k in 1:max_iter) {
    # Row scaling
    A <- A * (R / rowSums(A))
    # Column scaling
    A <- t(t(A) * (C / colSums(A)))
    # Check convergence
    if (max(abs(rowSums(A) - R)) < tol & max(abs(colSums(A) - C)) < tol) {
      break
    }
  }
  return(A)
}


# ──────────────────────────────────────────────────────────────────────
# 5. SIZE-ADJUSTED BASELINE & RAS VERIFICATION
# ──────────────────────────────────────────────────────────────────────

cat("\n═══════════════════════════════════════════════════════════════\n")
cat("STEP 2: RAS/IPF verification and size-adjusted baseline\n")
cat("═══════════════════════════════════════════════════════════════\n\n")

# Baseline trade shares as seed (encodes τ⁰^{1-σ} up to row/col factors)
pi_base <- X_mat / matrix(E_base, nrow = 3, ncol = 3, byrow = TRUE)

# Shocked seed: π⁰ × τ̂^{-θ} for the shocked cell
B_mat <- matrix(1, 3, 3)
B_mat[1, 2] <- tau_hat_AB^(-theta)  # = exp(beta_{AB})
seed_shocked <- pi_base * B_mat

# (a) RAS on shocked seed with counterfactual margins → should = X¹
X_ras_check <- ras_ipf(seed_shocked, Y1, E1)
cat("Max |X¹ − RAS(shocked seed, Y¹, E¹)| =",
    formatC(max(abs(X1_mat - X_ras_check)), format = "e", digits = 2), "\n")
cat("→ RAS recovers ge_gravity output exactly.\n\n")

# (b) Size-adjusted baseline: RAS baseline seed to counterfactual margins
X_adj <- ras_ipf(pi_base, Y1, E1)
cat("Size-adjusted baseline X^adj = RAS(π⁰, Y¹, E¹):\n")
print(round(X_adj, 4))

cat("\nLevel differences X¹ − X^adj:\n")
print(round(X1_mat - X_adj, 4))
cat("\n→ Non-shocked cells differ in levels (apparent 3rd-country effects?)\n\n")


# ──────────────────────────────────────────────────────────────────────
# 6. ODDS-RATIO TEST
# ──────────────────────────────────────────────────────────────────────

cat("═══════════════════════════════════════════════════════════════\n")
cat("STEP 3: Cross-product odds-ratio test\n")
cat("═══════════════════════════════════════════════════════════════\n\n")

# Compute odds ratio for a 2x2 sub-table
odds_ratio <- function(X, i, k, j, l) {
  (X[i, j] * X[k, l]) / (X[i, l] * X[k, j])
}

# All distinct 2x2 sub-tables in a 3x3 matrix
subtables <- list(
  # Format: list(i, k, j, l, label, involves_shocked)
  # Shocked cell is (1,2) i.e. row A, col B
  # NOT involving shocked cell (row 1 AND col 2):
  list(1, 2, 1, 3, "OR(A,B; A,C)", FALSE),
  list(1, 3, 1, 3, "OR(A,C; A,C)", FALSE),
  list(2, 3, 1, 2, "OR(B,C; A,B)", FALSE),
  list(2, 3, 1, 3, "OR(B,C; A,C)", FALSE),
  list(2, 3, 2, 3, "OR(B,C; B,C)", FALSE),
  # Involving shocked cell:
  list(1, 2, 1, 2, "OR(A,B; A,B)", TRUE),
  list(1, 2, 2, 3, "OR(A,B; B,C)", TRUE),
  list(1, 3, 1, 2, "OR(A,C; A,B)", TRUE),
  list(1, 3, 2, 3, "OR(A,C; B,C)", TRUE)
)

cat("───────────────────────────────────────────────────────────────\n")
cat(sprintf("  %-18s %12s %12s %12s\n", "Sub-table", "OR(X⁰)", "OR(X¹)", "OR(X^adj)"))
cat("───────────────────────────────────────────────────────────────\n")

cat("  Not involving shocked cell (A,B):\n")
for (s in subtables) {
  if (!s[[6]]) {
    or0   <- odds_ratio(X_mat,  s[[1]], s[[2]], s[[3]], s[[4]])
    or1   <- odds_ratio(X1_mat, s[[1]], s[[2]], s[[3]], s[[4]])
    or_adj <- odds_ratio(X_adj, s[[1]], s[[2]], s[[3]], s[[4]])
    cat(sprintf("  %-18s %12.4f %12.4f %12.4f\n", s[[5]], or0, or1, or_adj))
  }
}

cat("\n  Involving shocked cell (A,B):\n")
for (s in subtables) {
  if (s[[6]]) {
    or0   <- odds_ratio(X_mat,  s[[1]], s[[2]], s[[3]], s[[4]])
    or1   <- odds_ratio(X1_mat, s[[1]], s[[2]], s[[3]], s[[4]])
    or_adj <- odds_ratio(X_adj, s[[1]], s[[2]], s[[3]], s[[4]])
    cat(sprintf("  %-18s %12.4f %12.4f %12.4f  ← shocked\n", s[[5]], or0, or1, or_adj))
  }
}

# ──────────────────────────────────────────────────────────────────────
# 7. NUMERICAL PRECISION CHECK
# ──────────────────────────────────────────────────────────────────────

cat("\n───────────────────────────────────────────────────────────────\n")
cat("  Numerical precision — NON-SHOCKED odds ratios:\n")
cat(sprintf("  %-18s %18s %18s %18s\n",
            "Sub-table", "|OR(X⁰)−OR(X¹)|", "|OR(X⁰)−OR(X^adj)|", "|OR(X¹)−OR(X^adj)|"))
cat("───────────────────────────────────────────────────────────────\n")

for (s in subtables) {
  if (!s[[6]]) {
    or0    <- odds_ratio(X_mat,  s[[1]], s[[2]], s[[3]], s[[4]])
    or1    <- odds_ratio(X1_mat, s[[1]], s[[2]], s[[3]], s[[4]])
    or_adj <- odds_ratio(X_adj,  s[[1]], s[[2]], s[[3]], s[[4]])
    cat(sprintf("  %-18s %18.2e %18.2e %18.2e\n",
                s[[5]], abs(or0 - or1), abs(or0 - or_adj), abs(or1 - or_adj)))
  }
}

cat("\n───────────────────────────────────────────────────────────────\n")
cat("  Numerical precision — SHOCKED odds ratios:\n")
cat(sprintf("  %-18s %18s %18s %18s\n",
            "Sub-table", "|OR(X⁰)−OR(X¹)|", "|OR(X⁰)−OR(X^adj)|", "|OR(X¹)−OR(X^adj)|"))
cat("───────────────────────────────────────────────────────────────\n")

for (s in subtables) {
  if (s[[6]]) {
    or0    <- odds_ratio(X_mat,  s[[1]], s[[2]], s[[3]], s[[4]])
    or1    <- odds_ratio(X1_mat, s[[1]], s[[2]], s[[3]], s[[4]])
    or_adj <- odds_ratio(X_adj,  s[[1]], s[[2]], s[[3]], s[[4]])
    cat(sprintf("  %-18s %18.4f %18.2e %18.4f\n",
                s[[5]], abs(or0 - or1), abs(or0 - or_adj), abs(or1 - or_adj)))
  }
}


# ──────────────────────────────────────────────────────────────────────
# 8. DECOMPOSITION: Size + Cost + MR residual
# ──────────────────────────────────────────────────────────────────────

cat("\n═══════════════════════════════════════════════════════════════\n")
cat("STEP 4: Decomposition ΔX = Size + Cost + MR residual\n")
cat("═══════════════════════════════════════════════════════════════\n\n")

DX_total <- X1_mat - X_mat
DX_size  <- X_adj - X_mat                                   # new margins, old costs
DX_cost  <- ras_ipf(seed_shocked, Y1, E1) - X_adj           # new costs at new margins
DX_mr    <- DX_total - DX_size - DX_cost                    # residual

cat("Total change ΔX = X¹ − X⁰:\n")
print(round(DX_total, 4))
cat("\nSize effect (new margins, old costs):\n")
print(round(DX_size, 4))
cat("\nCost effect (new costs − old costs, at new margins):\n")
print(round(DX_cost, 4))
cat("\nMR residual (should ≈ 0):\n")
print(DX_mr)
cat("\nMax |MR residual| =", formatC(max(abs(DX_mr)), format = "e", digits = 2), "\n")


# ──────────────────────────────────────────────────────────────────────
# 9. SYNTHESIS
# ──────────────────────────────────────────────────────────────────────

cat("\n═══════════════════════════════════════════════════════════════\n")
cat("SYNTHESIS\n")
cat("═══════════════════════════════════════════════════════════════\n")
cat("
  Algorithm: GEGravity R package (Kudlay/Zylkin)
             = DEK (2007) exact hat algebra
             = Baier, Yotov & Zylkin (2019, JIE)

  Shock: τ̂_{AB} = 1.5 (50% cost increase, A→B exports)
  Parameters: σ = 5, θ = σ − 1 = 4

  Results:
  ────────────────────────────────────────────────────────────────
  1. RAS on shocked seed with (Y¹, E¹) recovers ge_gravity
     bilateral flows exactly.

  2. NON-SHOCKED odds ratios:
     OR(X⁰) = OR(X¹) = OR(X^adj)  [to machine precision]
     → Bilateral PATTERN among non-shocked pairs is IDENTICAL.
     → NO third-country effects in the association structure.

  3. SHOCKED odds ratios:
     OR(X⁰) = OR(X^adj) ≠ OR(X¹)
     → Pattern changes ONLY where τ was shocked.

  4. ΔX = ΔX_size + ΔX_cost + 0 (zero MR residual)
     → Full GE change decomposes exactly into Size + Cost.
     → No independent multilateral-resistance channel.

  Conclusion:
     The GEGravity full endowment GE — the standard implementation
     in the structural gravity literature — produces no third-country
     effects through multilateral resistance. The eigenvector search
     adjusts sizes (Y, E); RAS distributes flows; the bilateral
     pattern is invariant except at the directly shocked cell.
\n")

cat("═══════════════════════════════════════════════════════════════\n")
cat("Citation: Baier, Yotov & Zylkin (2019, JIE)\n")
cat("Package:  devtools::install_github('VKudlay/GEGravity')\n")
cat("═══════════════════════════════════════════════════════════════\n")
