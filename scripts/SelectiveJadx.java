// Original research utility: load an input once and save only selected classes.
// Usage: java -Xmx6g -cp tools/bin/jadx/lib/jadx-1.5.6-all.jar scripts/SelectiveJadx.java INPUT OUTPUT REGEX [fallback]
import java.io.File;
import java.util.regex.Pattern;
import jadx.api.JadxArgs;
import jadx.api.JadxDecompiler;
import jadx.api.DecompilationMode;

class SelectiveJadx {
    public static void main(String[] argv) throws Exception {
        if (argv.length < 3) throw new IllegalArgumentException("INPUT OUTPUT REGEX [fallback]");
        JadxArgs args = new JadxArgs();
        args.setInputFile(new File(argv[0]));
        args.setOutDir(new File(argv[1]));
        args.setThreadsCount(4);
        args.setSkipResources(true);
        args.setInlineMethods(false);
        args.setInlineAnonymousClasses(false);
        // Bundled SDK android.R can mislabel OEM framework IDs. Keep numeric IDs.
        args.setReplaceConsts(false);
        Pattern pattern = Pattern.compile(argv[2]);
        args.setClassFilter(name -> pattern.matcher(name).find());
        if (argv.length > 3 && argv[3].equals("fallback")) {
            args.setDecompilationMode(DecompilationMode.FALLBACK);
        }
        try (JadxDecompiler jadx = new JadxDecompiler(args)) {
            jadx.load();
            jadx.save();
            System.out.println("JADX errors (review affected methods): " + jadx.getErrorsCount());
        }
    }
}
