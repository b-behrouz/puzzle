package com.example.puzzlepreview;

import android.os.Bundle;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    private static final String BACK_SCRIPT = """
        (() => {
          const dialog = document.querySelector('dialog[open]');
          if (dialog) {
            dialog.close();
            return true;
          }
          for (const [screen, control] of [
            ['result', 'result-back'],
            ['game', 'game-back'],
            ['selection', 'selection-back'],
            ['categories', 'category-back']
          ]) {
            const page = document.getElementById(screen);
            if (page && !page.hidden) {
              document.getElementById(control).click();
              return true;
            }
          }
          return false;
        })()
        """;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (getBridge() == null) return;

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                getBridge().getWebView().evaluateJavascript(BACK_SCRIPT, handled -> {
                    if (!"true".equals(handled) && !isFinishing()) {
                        setEnabled(false);
                        getOnBackPressedDispatcher().onBackPressed();
                        setEnabled(true);
                    }
                });
            }
        });
    }
}
