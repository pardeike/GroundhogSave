using RimWorld;
using System;
using UnityEngine;
using Verse;

namespace GroundhogSave
{
	public class Dialog_NamePermadeathFile : Window
	{
		public string curName;
		public readonly Action<string> onSave;

		static readonly Color commitmentColor = new(1f, 0.3f, 0.35f);
		static readonly Color reloadAnytimeColor = new(0.3f, 1f, 0.35f);

		static readonly string commitmentModeString = "CommitmentMode".TranslateWithBackup("PermadeathMode");
		static readonly string reloadModeString = "ReloadAnytimeMode".Translate();
		static readonly string titleText = "GroundhogIntroduction".Translate(commitmentModeString.Colorize(commitmentColor), reloadModeString.Colorize(reloadAnytimeColor));

		public override Vector2 InitialSize => new(520f, 220f);

		public Dialog_NamePermadeathFile(string curName, Action<string> onSave)
		{
			this.curName = curName;
			this.onSave = onSave;
			doCloseX = false;
			doCloseButton = false;
			forcePause = true;
			preventCameraMotion = false;
			preventDrawTutor = true;
			absorbInputAroundWindow = false;
			draggable = true;
			focusWhenOpened = true;
		}

		public override void OnAcceptKeyPressed()
		{
			if (GenText.IsValidFilename(curName))
			{
				Find.WindowStack.TryRemove(this, true);
				onSave?.Invoke(curName);
				Close();
			}
		}

		public override void DoWindowContents(Rect rect)
		{
			Text.Font = GameFont.Small;

			if (Event.current.type == EventType.KeyDown && !Find.WindowStack.GetsInput(this))
			{
				Event.current.Use();
				return;
			}

			var rectLabel = new Rect(0f, 0f, rect.width, rect.height);
			Widgets.Label(rectLabel, titleText);

			var rectTextField = new Rect(0f, 80f, rect.width / 2f + 70f, 35f);
			curName = Widgets.TextField(rectTextField, curName, 40, null);

			var rect1 = new Rect(0f, rect.height - 35f, rect.width / 2f - 10f, 35f);
			GUI.color = reloadAnytimeColor;
			if (Widgets.ButtonText(rect1, reloadModeString))
				Close();

			var rect2 = new Rect(rect.width / 2f + 10f, rect.height - 35f, rect.width / 2f - 10f, 35f);
			var valid = curName.Length > 0 && GenText.IsValidFilename(curName);
			GUI.color = valid ? commitmentColor : commitmentColor.SaturationChanged(0.5f);
			if (Widgets.ButtonText(rect2, commitmentModeString, true, true, valid))
				OnAcceptKeyPressed();

			GUI.color = Color.white;
		}
	}
}