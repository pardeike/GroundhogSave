using Brrainz;
using HarmonyLib;
using RimWorld;
using System.Collections.Generic;
using System.Reflection;
using Verse;

using static HarmonyLib.Code;

namespace GroundhogSave
{
	[StaticConstructorOnStartup]
	public static class Main
	{
		public static string suffixOriginal = " " + "PermadeathModeSaveSuffix".Translate();
		public static string suffixReplaced = " " + "PermastartModeSaveSuffix".Translate();

		static Main()
		{
			var harmony = new Harmony("net.pardeike.harmony.GroundhogSave");
			harmony.PatchAll();
			CrossPromotion.Install(76561197973010050);
		}
	}

	[HarmonyPatch]
	static class QuickTestPlayPatches
	{
		[HarmonyPatch(typeof(Root_Play), nameof(Root_Play.SetupForQuickTestPlay))]
		[HarmonyPostfix]
		static void Root_Play_SetupForQuickTestPlay_Postfix() => Game_InitNewGame_Patch.isQuickTestPlay = true;

		[HarmonyPatch(typeof(ScenarioLister), nameof(ScenarioLister.MarkDirty))]
		[HarmonyPostfix]
		static void ScenarioLister_MarkDirty_Postfix() => Game_InitNewGame_Patch.isQuickTestPlay = false;
	}

	[HarmonyPatch(typeof(GameInfo), nameof(GameInfo.ExposeData))]
	static class GameInfo_ExposeData_Patch
	{
		[HarmonyPriority(Priority.First)]
		static void Prefix(GameInfo __instance)
		{
			var fileName = __instance.permadeathModeUniqueName;
			if (fileName != null && fileName.EndsWith(Main.suffixReplaced))
			{
				fileName = fileName[..^Main.suffixReplaced.Length];
				__instance.permadeathModeUniqueName = fileName + Main.suffixOriginal;
			}
		}
	}

	[HarmonyPatch(typeof(PermadeathModeUtility), nameof(PermadeathModeUtility.CheckUpdatePermadeathModeUniqueNameOnGameLoad))]
	static class PermadeathModeUtility_CheckUpdatePermadeathModeUniqueNameOnGameLoad_Patch
	{
		static bool Prefix(string filename) => !Current.Game.Info.permadeathMode || !filename.EndsWith(Main.suffixReplaced);
	}

	[HarmonyPatch(typeof(Game), nameof(Game.InitNewGame))]
	static class Game_InitNewGame_Patch
	{
		public static bool isQuickTestPlay = false;

		static void Postfix()
		{
			if (isQuickTestPlay)
				return;

			var game = Current.Game;
			if (game == null || game.info == null)
				return;

			Find.WindowStack.Add(new Dialog_NamePermadeathFile("", fileName =>
			{
				if (!fileName.EndsWith(Main.suffixReplaced))
					fileName += Main.suffixReplaced;

				game.info.permadeathMode = true;
				game.info.permadeathModeUniqueName = fileName;
				GameDataSaveLoader.SaveGame(fileName);
			}));
		}
	}

	[HarmonyPatch(typeof(SavedGameLoaderNow), nameof(SavedGameLoaderNow.LoadGameFromSaveFileNow))]
	static class SavedGameLoaderNow_LoadGameFromSaveFileNow_Patch
	{
		static void Postfix()
		{
			var filename = Current.Game?.Info?.permadeathModeUniqueName;
			if (filename != null && filename.EndsWith(Main.suffixReplaced))
				Current.Game.Info.permadeathModeUniqueName = filename[..^Main.suffixReplaced.Length] + Main.suffixOriginal;
		}
	}

	[HarmonyPatch(typeof(StorytellerUI), nameof(StorytellerUI.DrawStorytellerSelectionInterface))]
	static class StorytellerUI_DrawStorytellerSelectionInterface_Patch
	{
		static readonly MethodInfo m_Gap = SymbolExtensions.GetMethodInfo((Listing l) => l.Gap(0f));
		static readonly MethodInfo m_AnomalyActive = AccessTools.PropertyGetter(typeof(ModsConfig), nameof(ModsConfig.AnomalyActive));

		static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> instructions)
		{
			var matcher = new CodeMatcher(instructions).MatchStartForward([Ldarg_S, Ldc_R4[15f], Callvirt[m_Gap]])
				.ThrowIfNotMatch("Failed to find 'infoListing.Gap(15f)' in DrawStorytellerSelectionInterface");
			var startPos = matcher.Pos;
			matcher = matcher.MatchStartForward([Call[m_AnomalyActive]]);
			var endPos = matcher.Pos - 1;
			return matcher.RemoveInstructionsInRange(startPos, endPos).InstructionEnumeration();
		}
	}
}