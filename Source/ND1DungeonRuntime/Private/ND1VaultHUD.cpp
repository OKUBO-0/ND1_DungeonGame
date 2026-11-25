#include "ND1Vault.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/Button.h"
#include "Components/Border.h"
#include "Components/ProgressBar.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "GameFramework/Character.h"
#include "EngineUtils.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "InputCoreTypes.h"

namespace VaultUI
{
    const FLinearColor Ink(0.025f,0.037f,0.059f,0.97f), White(0.87f,0.91f,0.92f), Muted(0.37f,0.46f,0.49f), Gold(0.94f,0.67f,0.30f), Teal(0.25f,0.85f,0.76f), Red(1,0.29f,0.28f);
    FString Clock(float Seconds) { const int32 Time=FMath::Max(0,FMath::FloorToInt(Seconds)); return FString::Printf(TEXT("%02d:%02d"),Time/60,Time%60); }
}
AND1VaultGameMode* UND1VaultHUD::Mode() const { return Cast<AND1VaultGameMode>(UGameplayStatics::GetGameMode(this)); }
void UND1VaultHUD::NativeConstruct() { Super::NativeConstruct(); SetIsFocusable(true); Build(); }
TSharedRef<SWidget> UND1VaultHUD::RebuildWidget()
{
    if (!WidgetTree) WidgetTree=NewObject<UWidgetTree>(this);
    if (!Canvas) Canvas=WidgetTree->ConstructWidget<UCanvasPanel>();
    WidgetTree->RootWidget=Canvas;
    return Super::RebuildWidget();
}
UTextBlock* UND1VaultHUD::Label(FName Name,const FString& Text,int32 Size,FLinearColor Color)
{
    auto* Widget=WidgetTree->ConstructWidget<UTextBlock>();
    Widget->SetText(FText::FromString(Text)); Widget->SetColorAndOpacity(FSlateColor(Color));
    auto Font=FCoreStyle::GetDefaultFontStyle(Size>=36?TEXT("Bold"):TEXT("Regular"),Size); Widget->SetFont(Font);
    Widget->SetShadowOffset(FVector2D(0,1)); Widget->SetShadowColorAndOpacity(FLinearColor(0,0,0,0.3f));
    Labels.Add(Name,Widget); return Widget;
}
void UND1VaultHUD::Button(UVerticalBox* Box,const FString& Text,FName Action,bool Primary)
{
    auto* Widget=WidgetTree->ConstructWidget<UButton>();
    FButtonStyle Style=Widget->GetStyle();
    FSlateBrush Brush=*FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"));
    Brush.TintColor=Primary?VaultUI::Gold:FLinearColor(0.07f,0.11f,0.14f,1);
    Style.SetNormal(Brush); Brush.TintColor=Primary?FLinearColor(1,0.8f,0.49f):FLinearColor(0.12f,0.22f,0.25f); Style.SetHovered(Brush);
    Brush.TintColor=VaultUI::Teal; Style.SetPressed(Brush); Widget->SetStyle(Style);
    auto* TextWidget=Label(NAME_None,Text,17,Primary?VaultUI::Ink:VaultUI::White); TextWidget->SetMargin(FMargin(24,16));
    Widget->AddChild(TextWidget); auto* LayoutSlot=Box->AddChildToVerticalBox(Widget); LayoutSlot->SetPadding(FMargin(0,0,0,10)); LayoutSlot->SetHorizontalAlignment(HAlign_Fill);
    if (Action==TEXT("Start")) Widget->OnClicked.AddDynamic(this,&UND1VaultHUD::StartClick);
    else if (Action==TEXT("Retry")) Widget->OnClicked.AddDynamic(this,&UND1VaultHUD::RetryClick);
    else if (Action==TEXT("Title")) Widget->OnClicked.AddDynamic(this,&UND1VaultHUD::TitleClick);
    else if (Action==TEXT("Next")) Widget->OnClicked.AddDynamic(this,&UND1VaultHUD::NextClick);
    else if (Action==TEXT("Resume")) Widget->OnClicked.AddDynamic(this,&UND1VaultHUD::ResumeClick);
    else if (Action==TEXT("Controls")) Widget->OnClicked.AddDynamic(this,&UND1VaultHUD::ControlsClick);
    else if (Action==TEXT("Back")) Widget->OnClicked.AddDynamic(this,&UND1VaultHUD::BackClick);
    else if (Action==TEXT("Quit")) Widget->OnClicked.AddDynamic(this,&UND1VaultHUD::QuitClick);
}
void UND1VaultHUD::Build()
{
    auto* GM=Mode(); if (!GM) return;
    if (!WidgetTree) WidgetTree=NewObject<UWidgetTree>(this);
    Labels.Empty(); StaminaBar=nullptr;
    if (!Canvas) Canvas=WidgetTree->ConstructWidget<UCanvasPanel>(); else Canvas->ClearChildren();
    WidgetTree->RootWidget=Canvas; BuiltState=GM->State;
    auto Place=[&](UWidget* Widget,FVector2D Position,FVector2D Size,FAnchors Anchors=FAnchors(0,0),FVector2D Alignment=FVector2D::ZeroVector)
    {
        auto* LayoutSlot=Canvas->AddChildToCanvas(Widget); LayoutSlot->SetAnchors(Anchors); LayoutSlot->SetPosition(Position); LayoutSlot->SetSize(Size); LayoutSlot->SetAlignment(Alignment); return LayoutSlot;
    };
    if (GM->State==EVaultState::Playing)
    {
        auto* Plate=WidgetTree->ConstructWidget<UBorder>(); Plate->SetBrushColor(FLinearColor(0.02f,0.04f,0.06f,0.86f)); Place(Plate,FVector2D(24,24),FVector2D(225,180));
        Place(Label(TEXT("Floor"),TEXT(""),12,VaultUI::Gold),FVector2D(40,36),FVector2D(200,24));
        Place(Label(TEXT("Score"),TEXT(""),28,VaultUI::White),FVector2D(40,60),FVector2D(200,38));
        Place(Label(TEXT("Time"),TEXT(""),13,VaultUI::Muted),FVector2D(40,99),FVector2D(200,22));
        Place(Label(TEXT("Health"),TEXT(""),13,VaultUI::Teal),FVector2D(40,126),FVector2D(200,22));
        Place(Label(TEXT("Pulse"),TEXT(""),11,VaultUI::Teal),FVector2D(40,172),FVector2D(200,22));
        StaminaBar=WidgetTree->ConstructWidget<UProgressBar>(); StaminaBar->SetFillColorAndOpacity(VaultUI::Teal);
        Place(StaminaBar,FVector2D(40,154),FVector2D(190,5));
        auto* Objective=WidgetTree->ConstructWidget<UBorder>(); Objective->SetBrushColor(FLinearColor(0.02f,0.04f,0.06f,0.84f));
        Place(Objective,FVector2D(0,24),FVector2D(340,70),FAnchors(0.5f,0),FVector2D(0.5f,0));
        auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>(); Objective->AddChild(Stack);
        auto* First=Stack->AddChildToVerticalBox(Label(TEXT("Sigils"),TEXT(""),22,VaultUI::Gold)); First->SetHorizontalAlignment(HAlign_Center); First->SetPadding(FMargin(0,7,0,0));
        auto* Second=Stack->AddChildToVerticalBox(Label(TEXT("Alert"),TEXT(""),11,VaultUI::Teal)); Second->SetHorizontalAlignment(HAlign_Center);
        Place(Label(TEXT("Target"),TEXT(""),12,VaultUI::Gold),FVector2D(-224,238),FVector2D(210,34),FAnchors(1,0));
        Place(Label(TEXT("Message"),TEXT(""),16,VaultUI::White),FVector2D(0,-76),FVector2D(850,30),FAnchors(0.5f,1),FVector2D(0.5f,0));
        Labels[TEXT("Message")]->SetJustification(ETextJustify::Center);
        Place(Label(TEXT("Help"),TEXT("WASD  MOVE     ARROWS  CAMERA     SHIFT  SPRINT     SPACE  PULSE     P  PAUSE"),11,VaultUI::White),FVector2D(0,-30),FVector2D(850,22),FAnchors(0.5f,1),FVector2D(0.5f,0));
        Labels[TEXT("Help")]->SetJustification(ETextJustify::Center);
        Refresh(); return;
    }
    auto* Back=WidgetTree->ConstructWidget<UBorder>(); Back->SetBrushColor(VaultUI::Ink); auto* Background=Place(Back,FVector2D::ZeroVector,FVector2D::ZeroVector,FAnchors(0,0,1,1)); Background->SetOffsets(FMargin(0));
    auto* Box=WidgetTree->ConstructWidget<UVerticalBox>(); auto* Panel=Place(Box,FVector2D::ZeroVector,FVector2D(470,570),FAnchors(0.085f,0.12f)); Panel->SetAutoSize(true);
    auto Add=[&](FName Name,const FString& Text,int32 Size,FLinearColor Color,FMargin ItemPadding=FMargin(0,0,0,15))
    {
        auto* LayoutSlot=Box->AddChildToVerticalBox(Label(Name,Text,Size,Color)); LayoutSlot->SetPadding(ItemPadding);
    };
    Add(TEXT("Kicker"),TEXT("ND1  /  DUNGEON EXPLORATION"),12,VaultUI::Gold,FMargin(0,0,0,25));
    const auto* Run=GM->Run();
    if (GM->State==EVaultState::Title)
    {
        Add(TEXT("Heading"),TEXT("THE\nECHO VAULT"),58,VaultUI::White,FMargin(0,0,0,20));
        Add(TEXT("Description"),TEXT("Recover the sigils. Outwit the sentinels.\nFind your way out of two forgotten vaults."),16,VaultUI::Muted,FMargin(0,0,0,28));
        Button(Box,TEXT("BEGIN EXPEDITION  /  ENTER"),TEXT("Start"),true);
        Button(Box,TEXT("HOW TO PLAY"),TEXT("Controls")); Button(Box,TEXT("QUIT"),TEXT("Quit"));
    }
    else if (GM->State==EVaultState::Controls)
    {
        Add(TEXT("Heading"),TEXT("KNOW THE VAULT"),38,VaultUI::White);
        Add(TEXT("Instructions"),TEXT("W A S D     Move relative to the camera\nARROWS    Orbit the camera\nSHIFT         Sprint / consumes stamina\nSPACE        Echo pulse / stuns nearby slimes\nP or ESC    Pause\n\nTouch blue relics to score points.\nCollect all 3 amber sigils to open the gate.\nGreen crystals restore one vitality.\nChain relics within 5 seconds for up to x5.\nPulse costs 35 stamina, recharges in 6 sec.\nThe minimap reveals the places you explore."),16,VaultUI::White,FMargin(0,0,0,25));
        Button(Box,TEXT("BACK"),TEXT("Back"),true);
    }
    else
    {
        const FString Heading=GM->State==EVaultState::Paused?TEXT("TAKE A BREATH"):GM->State==EVaultState::FloorClear?TEXT("SEAL BROKEN"):GM->State==EVaultState::Victory?TEXT("VAULT RESTORED"):TEXT("THE VAULT\nCLAIMED YOU");
        Add(TEXT("Heading"),Heading,44,GM->State==EVaultState::GameOver?VaultUI::Red:VaultUI::White,FMargin(0,0,0,25));
        if (Run) Add(TEXT("Results"),FString::Printf(TEXT("SCORE    %06d\nTIME        %s\nVITALITY  %d / 3"),Run->Score,*VaultUI::Clock(Run->Seconds),Run->Health),21,VaultUI::Gold,FMargin(0,0,0,30));
        if (GM->State==EVaultState::Paused) { Button(Box,TEXT("RESUME"),TEXT("Resume"),true); Button(Box,TEXT("HOW TO PLAY"),TEXT("Controls")); }
        else if (GM->State==EVaultState::FloorClear)
        {
            Add(TEXT("NextHint"),TEXT("The Sunken Core awaits.\nTime and vitality bonuses added. +1 vitality."),16,VaultUI::Muted);
            Button(Box,TEXT("DESCEND TO FLOOR 02"),TEXT("Next"),true);
        }
        else if (GM->State==EVaultState::GameOver) Button(Box,TEXT("RETRY THIS FLOOR"),TEXT("Retry"),true);
        else Button(Box,TEXT("ANOTHER EXPEDITION"),TEXT("Start"),true);
        Button(Box,TEXT("RETURN TO TITLE"),TEXT("Title"));
    }
    if (Run && Run->Record)
    {
        const FString Best=FString::Printf(TEXT("PERSONAL ARCHIVE\n\nBEST SCORE     %06d\nBEST CLEAR     %s\nVAULTS RESTORED     %d"),Run->Record->BestScore,Run->Record->BestSeconds>0?*VaultUI::Clock(Run->Record->BestSeconds):TEXT("--:--"),Run->Record->CompletedRuns);
        Place(Label(TEXT("Record"),Best,13,VaultUI::Muted),FVector2D(-325,-160),FVector2D(300,140),FAnchors(1,1));
    }
    Place(Label(TEXT("Footer"),TEXT("TWO FLOORS  /  ONE WAY OUT"),11,VaultUI::Muted),FVector2D(0,-28),FVector2D(400,20),FAnchors(0.085f,1));
}
void UND1VaultHUD::Refresh()
{
    auto* GM=Mode(); if (!GM) return;
    if (BuiltState!=GM->State) { Build(); return; }
    if (GM->State!=EVaultState::Playing || !GM->Run()) return;
    const auto* Run=GM->Run();
    auto Set=[&](FName Name,const FString& Value) { if (Labels.Contains(Name)) Labels[Name]->SetText(FText::FromString(Value)); };
    Set(TEXT("Floor"),FString::Printf(TEXT("FLOOR  %02d / 02"),Run->Floor));
    Set(TEXT("Score"),FString::Printf(TEXT("%06d"),Run->Score)); Set(TEXT("Time"),TEXT("EXPEDITION  ")+VaultUI::Clock(Run->Seconds));
    Set(TEXT("Health"),FString::Printf(TEXT("VITALITY  %d / 3"),Run->Health));
    Set(TEXT("Sigils"),FString::Printf(TEXT("SIGILS  %d / %d"),GM->Sigils,GM->LevelInfo?GM->LevelInfo->RequiredSigils:3));
    Set(TEXT("Alert"),GM->Alerted?TEXT("SPOTTED  /  BREAK LINE OF SIGHT"):GM->GateOpen()?TEXT("GATE UNSEALED  /  REACH THE EXIT"):TEXT("UNSEEN  /  RECOVER THE AMBER SIGILS"));
    Labels[TEXT("Alert")]->SetColorAndOpacity(FSlateColor(GM->Alerted?VaultUI::Red:VaultUI::Teal));
    Set(TEXT("Pulse"),GM->PulseCooldown>0?FString::Printf(TEXT("ECHO PULSE  %.1fs"),GM->PulseCooldown):TEXT("ECHO PULSE  READY  [SPACE]"));
    Set(TEXT("Message"),GM->MessageSeconds>0?GM->Message:TEXT(""));
    if (StaminaBar) StaminaBar->SetPercent(GM->Stamina/100);
    if (GM->Player()) Set(TEXT("Target"),FString::Printf(TEXT("%s   %.0fm"),GM->GateOpen()?TEXT("EXIT"):TEXT("NEAREST SIGIL"),FVector::Dist2D(GM->Player()->GetActorLocation(),GM->NearestObjective())/100));
}
FReply UND1VaultHUD::NativeOnKeyDown(const FGeometry& Geometry,const FKeyEvent& Event)
{
    auto* GM=Mode(); if (!GM) return Super::NativeOnKeyDown(Geometry,Event);
    if (Event.GetKey()==EKeys::Enter && GM->State==EVaultState::Title) { GM->StartRun(); return FReply::Handled(); }
    if (Event.GetKey()==EKeys::Escape || Event.GetKey()==EKeys::P)
    {
        if (GM->State==EVaultState::Paused) GM->TogglePause();
        else if (GM->State==EVaultState::Controls) GM->BackFromControls();
        return FReply::Handled();
    }
    return Super::NativeOnKeyDown(Geometry,Event);
}
int32 UND1VaultHUD::NativePaint(const FPaintArgs& Args,const FGeometry& Geometry,const FSlateRect& CullingRect,FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,bool ParentEnabled) const
{
    int32 Result=Super::NativePaint(Args,Geometry,CullingRect,Elements,Layer,Style,ParentEnabled);
    const auto* GM=Mode(); if (!GM) return Result;
    const FVector2D Size=Geometry.GetLocalSize(); const auto* Brush=FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"));
    auto Box=[&](FVector2D Pos,FVector2D Extent,FLinearColor Color) { FSlateDrawElement::MakeBox(Elements,Result+1,Geometry.ToPaintGeometry(Extent,FSlateLayoutTransform(Pos)),Brush,ESlateDrawEffect::None,Color); };
    auto Lines=[&](TArray<FVector2D> Points,FLinearColor Color,float Width=1.5f) { FSlateDrawElement::MakeLines(Elements,Result+2,Geometry.ToPaintGeometry(),Points,ESlateDrawEffect::None,Color,true,Width); };
    if (GM->State!=EVaultState::Playing)
    {
        const FVector2D Center(Size.X*0.76f,Size.Y*0.36f); const float Radius=FMath::Min(130.0f,Size.X*0.15f);
        for (int32 Ring=0;Ring<3;++Ring)
        {
            TArray<FVector2D> Points; const float R=Radius*(1-Ring*0.24f);
            for (int32 I=0;I<=48;++I) { const float A=I*2*PI/48; Points.Add(Center+FVector2D(FMath::Cos(A),FMath::Sin(A))*R); }
            Lines(Points,FLinearColor(0.55f,0.45f,0.28f,0.55f-Ring*0.1f));
        }
        Lines({Center+FVector2D(0,-Radius*0.65f),Center+FVector2D(Radius*0.45f,0),Center+FVector2D(0,Radius*0.65f),Center+FVector2D(-Radius*0.45f,0),Center+FVector2D(0,-Radius*0.65f)},VaultUI::Gold,2);
        Lines({Center+FVector2D(0,-Radius*0.35f),Center+FVector2D(0,Radius*0.35f)},VaultUI::Teal,3);
        return Result+3;
    }
    if (!GM->LevelInfo || !GM->Player()) return Result;
    const AND1VaultLevel* Info=GM->LevelInfo; const int32 Rows=Info->Grid.Num();
    const int32 Columns=Rows?Info->Grid[0].Len():0;
    const FVector2D Origin(Size.X-224,24); const float Tile=FMath::Min(14.0f,174.0f/FMath::Max(1,FMath::Max(Rows,Columns)));
    Box(Origin,FVector2D(200,202),FLinearColor(0.018f,0.033f,0.05f,0.93f));
    const FVector2D Map=Origin+FVector2D(12,15);
    for (int32 Y=0;Y<Rows;++Y) for (int32 X=0;X<Info->Grid[Y].Len();++X)
    {
        if (!GM->Explored.Contains(FIntPoint(X,Y))) continue;
        const bool Wall=Info->Grid[Y][X]==TEXT('#');
        Box(Map+FVector2D(X*Tile,Y*Tile),FVector2D(Tile-1,Tile-1),Wall?FLinearColor(0.19f,0.25f,0.28f):FLinearColor(0.065f,0.105f,0.12f));
    }
    auto MapPoint=[&](FVector World){ return Map+FVector2D((World.X-Info->Origin.X)/Info->CellSize+0.5f,(World.Y-Info->Origin.Y)/Info->CellSize+0.5f)*Tile; };
    for (TActorIterator<AND1VaultPickup> It(GetWorld());It;++It) if (It->Kind==EVaultPickup::Sigil)
    {
        const FVector World=It->GetActorLocation()-Info->Origin; const FIntPoint Cell(FMath::RoundToInt(World.X/Info->CellSize),FMath::RoundToInt(World.Y/Info->CellSize));
        if (GM->Explored.Contains(Cell)) Box(MapPoint(It->GetActorLocation())-FVector2D(2,2),FVector2D(4,4),VaultUI::Gold);
    }
    if (GM->GateOpen()) for (TActorIterator<AND1VaultGate> It(GetWorld());It;++It) Box(MapPoint(It->GetActorLocation())-FVector2D(3,3),FVector2D(6,6),VaultUI::Teal);
    const FVector2D P=MapPoint(GM->Player()->GetActorLocation());
    const FVector V=GM->Player()->GetActorForwardVector(); const FVector2D Forward(V.X,V.Y),Right(-V.Y,V.X);
    Lines({P+Forward*6,P-Forward*4+Right*4,P-Forward*4-Right*4,P+Forward*6},VaultUI::Teal,2);
    return Result+3;
}
void UND1VaultHUD::StartClick(){ if (Mode()) Mode()->StartRun(); }
void UND1VaultHUD::RetryClick(){ if (Mode()) Mode()->RestartFloor(); }
void UND1VaultHUD::TitleClick(){ if (Mode()) Mode()->ReturnToTitle(); }
void UND1VaultHUD::NextClick(){ if (Mode()) Mode()->ContinueFloor(); }
void UND1VaultHUD::ResumeClick(){ if (Mode()) Mode()->TogglePause(); }
void UND1VaultHUD::ControlsClick(){ if (Mode()) Mode()->ShowControls(); }
void UND1VaultHUD::BackClick(){ if (Mode()) Mode()->BackFromControls(); }
void UND1VaultHUD::QuitClick(){ UKismetSystemLibrary::QuitGame(this,UGameplayStatics::GetPlayerController(this,0),EQuitPreference::Quit,false); }
