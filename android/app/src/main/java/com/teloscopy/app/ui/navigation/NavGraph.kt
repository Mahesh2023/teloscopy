package com.teloscopy.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.teloscopy.app.ui.screens.AnalysisScreen
import com.teloscopy.app.ui.screens.HomeScreen
import com.teloscopy.app.ui.screens.ProfileAnalysisScreen
import com.teloscopy.app.ui.screens.ResultsScreen
import com.teloscopy.app.ui.screens.SettingsScreen
import com.teloscopy.app.viewmodel.AnalysisViewModel
import com.teloscopy.app.viewmodel.ProfileViewModel

/**
 * Sealed class defining every navigable screen in the Teloscopy app.
 *
 * Each subclass carries its Compose Navigation route string. Screens
 * that accept arguments expose a helper function to build the concrete
 * route with the argument value substituted in.
 */
sealed class Screen(val route: String) {

    /** Landing / home screen with navigation to all features. */
    data object Home : Screen("home")

    /** Full analysis screen (image upload + user profile). */
    data object Analysis : Screen("analysis")

    /**
     * Results screen for a completed (or in-progress) analysis job.
     *
     * The route contains a `{jobId}` path parameter.  Use [createRoute]
     * to build a concrete route for navigation.
     */
    data object Results : Screen("results/{jobId}") {
        /** Build a concrete route with the given [jobId]. */
        fun createRoute(jobId: String): String = "results/$jobId"
    }

    /** Profile-only analysis (no image required). */
    data object ProfileAnalysis : Screen("profile_analysis")

    /** Application settings. */
    data object Settings : Screen("settings")
}

/**
 * Top-level navigation host for the Teloscopy app.
 *
 * Wires each [Screen] route to its composable destination, creates
 * Hilt-scoped ViewModels where needed, and forwards navigation
 * callbacks so screens remain decoupled from the [NavHostController].
 *
 * @param navController The [NavHostController] that drives navigation.
 * @param modifier      Optional [Modifier] applied to the [NavHost].
 */
@Composable
fun TeloscopyNavHost(
    navController: NavHostController,
    modifier: Modifier = Modifier
) {
    NavHost(
        navController = navController,
        startDestination = Screen.Home.route,
        modifier = modifier
    ) {
        // -- Home -----------------------------------------------------------
        composable(Screen.Home.route) {
            HomeScreen(
                onNavigateToAnalysis = {
                    navController.navigate(Screen.Analysis.route)
                },
                onNavigateToProfile = {
                    navController.navigate(Screen.ProfileAnalysis.route)
                },
                onNavigateToSettings = {
                    navController.navigate(Screen.Settings.route)
                }
            )
        }

        // -- Analysis (image + profile) -------------------------------------
        composable(Screen.Analysis.route) {
            val viewModel: AnalysisViewModel = hiltViewModel()
            AnalysisScreen(
                viewModel = viewModel,
                onNavigateToResults = { jobId ->
                    navController.navigate(Screen.Results.createRoute(jobId))
                },
                onBack = {
                    navController.popBackStack()
                }
            )
        }

        // -- Results --------------------------------------------------------
        composable(
            route = Screen.Results.route,
            arguments = listOf(
                navArgument("jobId") { type = NavType.StringType }
            )
        ) { backStackEntry ->
            val jobId = backStackEntry.arguments?.getString("jobId") ?: ""
            val viewModel: AnalysisViewModel = hiltViewModel()
            ResultsScreen(
                jobId = jobId,
                viewModel = viewModel,
                onBack = {
                    navController.popBackStack()
                }
            )
        }

        // -- Profile Analysis (no image) ------------------------------------
        composable(Screen.ProfileAnalysis.route) {
            val viewModel: ProfileViewModel = hiltViewModel()
            ProfileAnalysisScreen(
                viewModel = viewModel,
                onBack = {
                    navController.popBackStack()
                }
            )
        }

        // -- Settings -------------------------------------------------------
        composable(Screen.Settings.route) {
            SettingsScreen(
                onBack = {
                    navController.popBackStack()
                }
            )
        }
    }
}
